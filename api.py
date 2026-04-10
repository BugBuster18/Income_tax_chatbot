import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

# Import everything from the main app
import config
from rag.vector_store import load_index
from rag.query_rewriter import rewrite_query
from rag.relevance import check_relevance
from rag.context_builder import build_irrelevant_response
from rag.structured_generator import generate_structured_data
from rag.final_response_generator import generate_final_response
from rag.retriever import retrieve

# Load validater
sys.path.append(str(config.BASE_DIR / "rule_engine" / "Mini-project"))
try:
    from validator import validate_all
except ImportError as e:
    print(f"Warning: Could not import rule_engine. validator: {e}")
    validate_all = None

app = FastAPI(title="Income Tax RAG API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import Optional, List

class ChatRequest(BaseModel):
    user_query: str
    current_query: str = ""
    contexts: Optional[List[str]] = None

# Global objects
_index = None
_chunks = None
_client = None

def get_globals():
    global _index, _chunks, _client
    if _index is None:
        _index = load_index()
    return _index, _chunks, _client

from main import initialise_index

@app.on_event("startup")
def startup_event():
    global _index, _chunks, _client
    if not config.GEMINI_API_KEY:
        print("ERROR: Set the GEMINI_API_KEY environment variable first.")
        sys.exit(1)
    
    print("Initialize index...")
    _index, _chunks = initialise_index(force_rebuild=False)
    _client = genai.Client(api_key=config.GEMINI_API_KEY)
    print("API is ready.")

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    global _index, _chunks, _client
    if _index is None:
        raise HTTPException(status_code=500, detail="Index not loaded")

    user_query = req.user_query
    current_query = req.current_query if req.current_query else user_query
    contexts = req.contexts

    if contexts is None:
        # Step 1 — rewrite + classify
        rewrite_result = rewrite_query(user_query, client=_client)
        rewritten = rewrite_result["rewritten_query"]
        is_tax = rewrite_result["is_tax_related"]

        if not is_tax:
            return build_irrelevant_response("Query not related to income tax")

        # Step 3 — retrieve
        results = retrieve(rewritten, _index, _chunks, client=_client)

        # Step 4 — hybrid relevance check
        rel = check_relevance(is_tax, results)

        if rel["status"] == "irrelevant":
            return build_irrelevant_response(rel["message"])

        # Step 5 — generate structured JSON from contexts
        contexts = [r["text"] for r in rel["results"]]
        
    structured_res = generate_structured_data(current_query, contexts, client=_client)

    if structured_res.get("status") == "need_more_info":
        return {
            "status": "need_more_info", 
            "question": structured_res.get("question", "I need more information."), 
            "current_query": current_query,
            "contexts": contexts
        }

    if structured_res.get("status") == "success" and validate_all is not None:
        user_data = structured_res.get("data", {})
        
        regime_pref = (user_data.get("regime") or "both").lower()
        if "both" in regime_pref or "compare" in regime_pref:
            user_data_old = {**user_data, "regime": "old"}
            user_data_new = {**user_data, "regime": "new"}
            
            val_old = validate_all(user_data_old)
            val_new = validate_all(user_data_new)
            
            validation_result = {
                "COMPARISON_MODE": True,
                "old_regime_result": val_old,
                "new_regime_result": val_new
            }
        else:
            validation_result = validate_all(user_data)
        
        final_answer = generate_final_response(current_query, validation_result, client=_client)
        
        return {
            "status": "success",
            "extracted_data": user_data,
            "rule_engine_result": validation_result,
            "final_answer": final_answer,
            "current_query": current_query,
            "contexts": contexts
        }
        
    return structured_res

class FollowupRequest(BaseModel):
    messages: List[dict]
    new_query: str

@app.post("/chat/followup")
def followup_endpoint(req: FollowupRequest):
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
        
    system_instruction = "You are a helpful income tax assistant. The user is asking a follow-up question about the tax calculation you just provided. Use the context of the conversation to answer them clearly and concisely. Do not ask them to run the calculation again unless they explicitly want a completely new scenario."
    
    contents = []
    for m in req.messages[-6:]: # Keep last 6 messages for context
        # map system to model
        role = "model" if m["role"] == "system" else "user"
        # Quick strip of markdown boldings for cleaner context if needed, but Gemini handles it fine
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
        
    contents.append({"role": "user", "parts": [{"text": req.new_query}]})
    
    response = _client.models.generate_content(
        model='gemini-2.5-flash',
        contents=contents,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3
        )
    )
    
    return {"status": "success", "reply": response.text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)







