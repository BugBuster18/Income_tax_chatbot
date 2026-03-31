import json
from google import genai

from rule_engine.schema_extractor import extract_schema
import config

SYSTEM_PROMPT_TEMPLATE = """\
You are an expert tax advisor system connecting a semantic search engine (RAG) to a strict rule engine.
Your goal is to extract structured data from the user query guided by the provided legal context, 
and output a JSON strictly adhering to the Target JSON Schema below.

User Query:
{query}

Retrieved Context:
{context}

Target JSON Schema expected by the Rule Engine:
{schema}

Instructions:
1. Populate the fields in the schema strictly based on the User Query.
2. If the query does not mention a value for a property, set it to `null`.
3. DO NOT hallucinate values.
4. Extract relevant investments into the correct deductions categories as permitted by the schema.
5. REQUIRED FIELDS: Determine what data is needed logically based on the User's intent and the Target JSON Schema. For general tax queries, base fields like `income` and `regime` are typically necessary. If the user mentions specific exemptions or deductions (e.g., HRA, 80D, NPS), inspect the schema to identify all related sub-fields (e.g., rent_paid, basic_salary, parents_age, etc.) and treat them as required.
6. If the User Query lacks ANY of the fields logically required to fulfill their request and compute taxes accurately, you MUST return a clarification JSON:
   {{"status": "need_more_info", "missing_fields": ["<list all missing fields>"], "question": "<Friendly question comprehensively asking for ALL missing details at once>"}}
7. Otherwise, if you have enough data to proceed (all required fields logically deduced from their intent are present), return:
   {{"status": "success", "data": <YOUR_POPULATED_JSON>}}

Output format: ONLY valid JSON (either `success` with `data` or `need_more_info`).
"""

def generate_structured_data(user_query, contexts, client: genai.Client | None = None):
    """
    Combines the user query, the RAG contexts, and the dynamically extracted Rule Engine schema
    to generate a structured JSON object.
    
    Returns
    -------
    dict
        {"status": "success", "data": {...}} OR
        {"status": "need_more_info", "missing_fields": [...], "question": "..."}
    """
    if client is None:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
    schema = extract_schema()
    
    # Combine contexts into a single text block
    joined_context = "\n".join([f"- {c}" for c in contexts]) if contexts else "No relevant context found."
    
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        query=user_query,
        context=joined_context,
        schema=json.dumps(schema, indent=2)
    )
    
    response = client.models.generate_content(
        model=config.GEMINI_LLM_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json", # Let's ask Gemini to strictly output JSON
        ),
    )
    
    raw = response.text.strip()
    
    # Strip markdown if any
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()
        
    try:
        parsed = json.loads(raw)
        return parsed
    except json.JSONDecodeError:
        print(f"[structured_generator] WARNING: could not parse LLM response:\n{raw}")
        return {
            "status": "error",
            "message": "Failed to generate structured data."
        }
