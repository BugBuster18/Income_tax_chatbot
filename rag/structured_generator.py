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
5. REGIME LOGIC: If the user explicitly states they want "old" or "new" regime, or "both/comparison", set `regime` exactly to that. If they DO NOT explicitly mention a regime preference, you MUST ask them by adding `regime` to `missing_fields`. Your clarification question should explicitly give them the option to choose: "Would you like your taxes calculated under the old regime, the new regime, or both (for comparison)?". If they list deductions like 80C or HRA, gently suggest comparing both. Do NOT assume a regime without their confirmation.
6. REQUIRED FIELDS: Identify other missing fields based on intent. If the User Query lacks ANY of the fields logically required (like basic income, or exact rent amounts if they clearly mentioned HRA), you MUST return a clarification JSON. CRITICAL: Your "question" string MUST ALWAYS format multiple missing details as a strict numbered list separated by newlines (e.g., "1. First question?\n2. Second question?"). Do NOT combine them into a single paragraph! Format:
   {{"status": "need_more_info", "missing_fields": ["<list all missing fields>"], "question": "I need more details:\n1. <First question>\n2. <Second question>"}}
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
