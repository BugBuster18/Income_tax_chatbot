import json
from error_codes import ErrorCodes

def validate_hra(data, adjusted_data):
    errors = []
    regime = (data.get("regime") or "new").lower()
    exemptions = data.get("exemptions") or {}

    if regime != "old":
        if exemptions.get("HRA"):
            errors.append(ErrorCodes.NOT_ALLOWED_IN_NEW_REGIME_HRA)
        adjusted_data.setdefault("exemptions", {})["HRA"] = 0
        return errors

    hra_details = exemptions.get("HRA") or {}
    if not isinstance(hra_details, dict) or not hra_details:
        adjusted_data.setdefault("exemptions", {})["HRA"] = 0
        return errors

    actual_hra = hra_details.get("hra_received") or 0
    basic_salary = hra_details.get("basic_salary") or data.get("basic_salary") or 0
    da = hra_details.get("da") or data.get("da") or 0
    rent_paid = hra_details.get("rent_paid") or 0
    is_metro = hra_details.get("is_metro") or False

    salary_base = basic_salary + da

    # Condition 1: Actual HRA received
    cond1 = actual_hra

    # Condition 2: 50% or 40% of Salary
    percent = 0.50 if is_metro else 0.40
    cond2 = percent * salary_base

    # Condition 3: Rent paid minus 10% of salary
    cond3 = max(0, rent_paid - (0.10 * salary_base))

    exempt_hra = min(cond1, cond2, cond3)
    
    adjusted_data.setdefault("exemptions", {})["HRA"] = exempt_hra

    # Optional: Log an error/warning if user claimed more than allowed
    claimed_hra = hra_details.get("claimed", actual_hra)
    if claimed_hra > exempt_hra:
        # We can append an error, but HRA is often just computed
        pass 

    return errors
