import json
from google import genai
import config

PROMPT_TEMPLATE = """\
You are an expert Indian Income Tax Advisor.
Based on the User Query and the calculated Results from our Tax Rule Engine, provide a final, clear, and helpful response to the user.

User Query (with any clarifications):
{query}

Tax Rule Engine Output (JSON):
{rule_engine_result}

Instructions:
1. Summarize the user's taxable income and total tax liability clearly.
2. If the Rule Engine Output contains `"COMPARISON_MODE": true`, structure your response to compare BOTH the Old Regime and New Regime clearly using a markdown table or side-by-side bullets. Highlight and strongly recommend the regime that results in the lower total tax liability.
3. If there are any `errors` in the rule engine output (like "NOT_ALLOWED_IN_NEW_REGIME" or limit exceeded messages), explain to the user why certain exemptions/deductions were disallowed under that specific regime.
4. Mention any adjustments made (e.g., if they requested 2 Lakh under 80C but the cap is 1.5 Lakh, explain the adjustment).
5. Break down the tax structure (taxable income, computed tax, cess, rebates) briefly so the user understands how the final computation was reached.
6. Keep the tone professional, helpful, and easily digestible. Format the response nicely using rich markdown (data tables, bold text).

Generate the final response now.
"""

def generate_final_response(user_query, rule_engine_result, client=None):
    if client is None:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
    prompt = PROMPT_TEMPLATE.format(
        query=user_query,
        rule_engine_result=json.dumps(rule_engine_result, indent=2)
    )
    
    response = client.models.generate_content(
        model=config.GEMINI_LLM_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.3,
        ),
    )
    
    return response.text.strip()
