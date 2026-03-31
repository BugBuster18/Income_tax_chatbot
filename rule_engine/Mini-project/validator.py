from deductions import validate_80c, validate_80d, validate_nps, validate_standard_deduction
from exemptions import validate_hra
from slabs import calculate_tax_slabs, calculate_rebate_87a, calculate_surcharge, calculate_cess
from regime import validate_regime
import json

def validate_all(data):
    """
    Main rule engine function.
    Given user data, applies all tax rules, aggregates errors, calculates tax liabilities.
    """
    valid_res = True
    errors = []
    adjusted_data = {}
    tax_computation = {}

    regime = (data.get("regime") or "new").lower()
    
    # 1. Z3 Regime Validations
    regime_errors = validate_regime(data)
    if regime_errors:
        errors.extend(regime_errors)

    # 2. Exemptions Validation
    exempt_errors = validate_hra(data, adjusted_data)
    errors.extend(exempt_errors)

    # 3. Deductions Validation
    deduct_errors = validate_80c(data, adjusted_data)
    errors.extend(deduct_errors)

    deduct_errors_80d = validate_80d(data, adjusted_data)
    errors.extend(deduct_errors_80d)

    nps_errors = validate_nps(data, adjusted_data)
    errors.extend(nps_errors)

    sd_errors = validate_standard_deduction(data, adjusted_data)
    errors.extend(sd_errors)

    # 4. Tax Computation
    # Gross Income
    income = data.get("income") or 0 # Base income/salary
    
    # Calculate Total Exemptions
    total_exemptions = sum(adjusted_data.get("exemptions", {}).values())
    
    # Calculate Total Deductions
    deductions = adjusted_data.get("deductions", {})
    total_deductions = sum(deductions.values())
    
    taxable_income = max(0, income - total_exemptions - total_deductions)
    tax_computation["taxable_income"] = taxable_income

    age = data.get("age") or 30
    
    # Calculate Basic Tax
    computed_tax = float(calculate_tax_slabs(taxable_income, regime, age))
    tax_computation["computed_tax"] = computed_tax

    # Calculate Rebate 87A
    rebate = float(calculate_rebate_87a(taxable_income, computed_tax, regime))
    tax_after_rebate = max(0.0, float(computed_tax - rebate))
    tax_computation["rebate_87a"] = rebate
    tax_computation["tax_after_rebate"] = tax_after_rebate

    # Calculate Surcharge
    surcharge = float(calculate_surcharge(taxable_income, tax_after_rebate, regime))
    tax_after_surcharge = tax_after_rebate + surcharge
    tax_computation["surcharge"] = surcharge

    # Calculate Cess
    cess = float(calculate_cess(tax_after_surcharge))
    total_tax_liability = float(tax_after_surcharge + cess)
    tax_computation["cess"] = cess
    tax_computation["total_tax_liability"] = total_tax_liability

    if len(errors) > 0:
        valid_res = False

    # Deduplicate errors
    errors = list(set(errors))

    return {
        "valid": valid_res,
        "errors": errors,
        "adjusted_data": adjusted_data,
        "tax_computation": tax_computation
    }
