import json
from error_codes import ErrorCodes

def validate_80c(data, adjusted_data):
    errors = []
    regime = (data.get("regime") or "new").lower()
    deductions = data.get("deductions") or {}
    
    # Check regime
    if regime != "old":
        if "80C" in deductions:
            errors.append(ErrorCodes.NOT_ALLOWED_IN_NEW_REGIME_80C)
        adjusted_data.setdefault("deductions", {})["80C"] = 0
        return errors

    # Calculate 80C Sum
    deductions_raw = deductions.get("80C") or {}
    if isinstance(deductions_raw, dict):
        total_80c = sum(float(v) for v in deductions_raw.values() if v is not None)
    else:
        total_80c = float(deductions_raw) if deductions_raw is not None else 0.0

    # Limit check
    max_limit = 150000
    if total_80c > max_limit:
        errors.append(ErrorCodes.LIMIT_EXCEEDED_80C)
        adjusted_data.setdefault("deductions", {})["80C"] = max_limit
    else:
        adjusted_data.setdefault("deductions", {})["80C"] = total_80c

    return errors


def validate_80d(data, adjusted_data):
    errors = []
    regime = (data.get("regime") or "new").lower()
    deductions = data.get("deductions") or {}

    if regime != "old":
        if "80D" in deductions:
            errors.append(ErrorCodes.NOT_ALLOWED_IN_NEW_REGIME_80D)
        adjusted_data.setdefault("deductions", {})["80D"] = 0
        return errors

    deductions_raw = deductions.get("80D") or {}
    if not isinstance(deductions_raw, dict):
        adjusted_data.setdefault("deductions", {})["80D"] = 0
        return errors

    age_self = data.get("age") or 30
    age_parents = data.get("parents_age") or 55

    health_self = deductions_raw.get("health_insurance_self")
    health_self = float(health_self) if health_self is not None else 0.0
    
    health_family = deductions_raw.get("health_insurance_family")
    health_family = float(health_family) if health_family is not None else 0.0
    
    self_family = health_self + health_family
    
    parents = deductions_raw.get("health_insurance_parents")
    parents = float(parents) if parents is not None else 0.0
    
    preventive = deductions_raw.get("preventive_checkup")
    preventive = float(preventive) if preventive is not None else 0.0

    # Preventive limit
    if preventive > 5000:
        preventive = 5000

    # Self limit calculation
    self_limit = 50000 if age_self >= 60 else 25000
    total_self = min(self_family + preventive, self_limit)

    # Prevent counting preventive twice
    remaining_preventive = max(0, preventive - (total_self - self_family))

    # Parents limit calculation
    parents_limit = 50000 if age_parents >= 60 else 25000
    total_parents = min(parents + remaining_preventive, parents_limit)

    total_80d = total_self + total_parents
    actual_claimed = self_family + parents + preventive

    if actual_claimed > total_80d:
        errors.append(ErrorCodes.LIMIT_EXCEEDED_80D)

    adjusted_data.setdefault("deductions", {})["80D"] = total_80d
    return errors


def validate_nps(data, adjusted_data):
    errors = []
    regime = (data.get("regime") or "new").lower()
    deductions = data.get("deductions") or {}
    deductions_nps = deductions.get("NPS") or {}
    
    if not isinstance(deductions_nps, dict):
        adjusted_data.setdefault("deductions", {})["NPS"] = 0
        return errors
        
    employee_contrib = deductions_nps.get("nps_employee") or deductions_nps.get("employee_80ccd1b")
    employee_contrib = float(employee_contrib) if employee_contrib is not None else 0.0
    
    employer_contrib = deductions_nps.get("nps_employer") or deductions_nps.get("employer_80ccd2")
    employer_contrib = float(employer_contrib) if employer_contrib is not None else 0.0
    
    # 80CCD(1B) is only for OLD regime
    adjusted_employee = 0
    if regime == "new" and employee_contrib > 0:
        errors.append(ErrorCodes.NOT_ALLOWED_IN_NEW_REGIME_80CCD1B)
    elif regime == "old":
        if employee_contrib > 50000:
            errors.append(ErrorCodes.LIMIT_EXCEEDED_NPS_80CCD1B)
            adjusted_employee = 50000
        else:
            adjusted_employee = employee_contrib

    # 80CCD(2) is available in both regimes
    basic_salary = data.get("basic_salary")
    basic_salary = float(basic_salary) if basic_salary is not None else 0.0
    
    da = data.get("da")
    da = float(da) if da is not None else 0.0
    
    salary_base = basic_salary + da
    
    employer_limit_percent = 0.14 if regime == "new" else 0.10
    employer_limit = salary_base * employer_limit_percent
    
    adjusted_employer = employer_contrib
    if employer_contrib > employer_limit:
        errors.append(ErrorCodes.LIMIT_EXCEEDED_NPS_80CCD2)
        adjusted_employer = employer_limit
        
    adjusted_data.setdefault("deductions", {})["NPS_80CCD1B"] = adjusted_employee
    adjusted_data.setdefault("deductions", {})["NPS_80CCD2"] = adjusted_employer

    return errors


def validate_standard_deduction(data, adjusted_data):
    errors = []
    regime = (data.get("regime") or "new").lower()
    
    salary = data.get("income")
    salary = float(salary) if salary is not None else 0.0
    
    deductions = data.get("deductions") or {}
    claimed = deductions.get("standard_deduction") or 0
    max_sd = 75000 if regime == "new" else 50000
    
    allowed_sd = min(salary, max_sd)
    
    if claimed > allowed_sd:
        errors.append(ErrorCodes.INVALID_STANDARD_DEDUCTION)
        
    adjusted_data.setdefault("deductions", {})["standard_deduction"] = allowed_sd
    
    return errors
