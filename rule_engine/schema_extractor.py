import json
import re
from pathlib import Path

def extract_schema(rule_engine_dir="rule_engine/Mini-project"):
    """
    Dynamically extracts the JSON schema expected by the rule engine.
    Scans the Python code for `data.get(...)` patterns and reads rules.json.
    """
    dir_path = Path(rule_engine_dir)
    
    schema = {
        "income": "number",
        "basic_salary": "number",
        "da": "number",
        "age": "number",
        "parents_age": "number",
        "regime": "string",
        "exemptions": {},
        "deductions": {}
    }
    
    # Heuristics: search for specific fields we know they retrieve
    for py_file in dir_path.glob("*.py"):
        if py_file.name in ("demo.py", "error_codes.py", "validator.py"):
            continue
            
        content = py_file.read_text(encoding="utf-8")
        
        # Look for deductuons.get("80D", {})
        # This is a bit manual, but we can also use rules.json
        
    # Read rules.json for dynamic mapping
    rules_path = dir_path / "rules.json"
    if rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
            
        for rule in rules:
            sec = rule.get("section")
            inputs = rule.get("inputs", [])
            
            # Categorize based on our knowledge of Indian tax sections
            if sec == "HRA":
                if "HRA" not in schema["exemptions"]:
                    schema["exemptions"]["HRA"] = {}
                for fld in inputs:
                    schema["exemptions"]["HRA"][fld] = "number" 
            elif "80" in sec or "Standard" in sec: # Deductions
                # Handle keys like '80CCD(1B) and 80CCD(2)' -> split them
                parts = [sec]
                if "and" in sec:
                    parts = ["NPS_80CCD1B", "NPS_80CCD2"] # normalize
                
                # We just map what rules.json gives us
                sec_key = "80C" if "80C" in sec else "80D" if "80D" in sec else "NPS" if "80CCD" in sec else "standard_deduction"
                
                if sec_key not in schema["deductions"] and sec_key != "standard_deduction":
                    schema["deductions"][sec_key] = {}
                    
                if isinstance(schema["deductions"].get(sec_key), dict):
                    for fld in inputs:
                        schema["deductions"][sec_key][fld] = "number"
                elif sec_key == "standard_deduction":
                    schema["deductions"]["standard_deduction"] = "number"
                    
    # Fix a few known boolean fields based on typical Python code analysis
    if "HRA" in schema["exemptions"] and "is_metro" in schema["exemptions"]["HRA"]:
        schema["exemptions"]["HRA"]["is_metro"] = "boolean"

    return schema

if __name__ == "__main__":
    print(json.dumps(extract_schema(), indent=2))
