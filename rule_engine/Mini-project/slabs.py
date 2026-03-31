def calculate_tax_slabs(taxable_income, regime="new", age=30):
    tax = 0.0
    if regime == "new":
        # FY 25-26 New Regime Slabs
        if taxable_income > 2400000:
            tax += (taxable_income - 2400000) * 0.30
            taxable_income = 2400000
        if taxable_income > 2000000:
            tax += (taxable_income - 2000000) * 0.25
            taxable_income = 2000000
        if taxable_income > 1600000:
            tax += (taxable_income - 1600000) * 0.20
            taxable_income = 1600000
        if taxable_income > 1200000:
            tax += (taxable_income - 1200000) * 0.15
            taxable_income = 1200000
        if taxable_income > 800000:
            tax += (taxable_income - 800000) * 0.10
            taxable_income = 800000
        if taxable_income > 400000:
            tax += (taxable_income - 400000) * 0.05
    else:
        # FY 25-26 Old Regime Slabs
        exemption_limit = 250000
        if age >= 80:
            exemption_limit = 500000
        elif age >= 60:
            exemption_limit = 300000

        if taxable_income > 1000000:
            tax += (taxable_income - 1000000) * 0.30
            taxable_income = 1000000
        if taxable_income > 500000:
            tax += (taxable_income - 500000) * 0.20
            taxable_income = 500000
        if taxable_income > exemption_limit:
            tax += (taxable_income - exemption_limit) * 0.05
    return tax


def calculate_rebate_87a(taxable_income, computed_tax, regime="new"):
    # Rebate 87A logic including marginal relief
    if regime == "new":
        threshold = 1200000
        max_rebate = 60000
    else:
        threshold = 500000
        max_rebate = 12500

    if taxable_income <= threshold:
        return min(computed_tax, max_rebate)

    # Marginal Relief for Rebate 87A
    # If income slightly exceeds threshold, relief is provided if
    # tax payable > (income - threshold)
    excess_income = taxable_income - threshold
    if computed_tax > excess_income:
        return computed_tax - excess_income # Rebate is the difference
    return 0


def calculate_surcharge(taxable_income, computed_tax_after_rebate, regime="new"):
    # Applicable if taxable income > 50L
    if taxable_income <= 5000000:
        return 0

    if taxable_income <= 10000000: # 50L to 1Cr
        surcharge_rate = 0.10
        base_tax = calculate_tax_slabs(5000000, regime)
        base_tax_after_rebate = base_tax - calculate_rebate_87a(5000000, base_tax, regime)
        threshold = 5000000
        excess_tax_on_threshold = base_tax_after_rebate # Actually surcharge is 0 on 50L
    elif taxable_income <= 20000000: # 1Cr to 2Cr
        surcharge_rate = 0.15
        base_tax = calculate_tax_slabs(10000000, regime)
        base_tax_after_rebate = base_tax - calculate_rebate_87a(10000000, base_tax, regime)
        # tax on 1Cr includes 10% surcharge
        base_tax_after_rebate *= 1.10
        threshold = 10000000
    elif taxable_income <= 50000000 and regime == "old": # 2Cr to 5Cr old regime
        surcharge_rate = 0.25
        base_tax = calculate_tax_slabs(20000000, regime)
        base_tax_after_rebate = base_tax * 1.15
        threshold = 20000000
    elif taxable_income > 50000000 and regime == "old": # >5Cr old regime
        surcharge_rate = 0.37
        base_tax = calculate_tax_slabs(50000000, regime)
        base_tax_after_rebate = base_tax * 1.25
        threshold = 50000000
    else: # >2Cr new regime (capped at 25%)
        surcharge_rate = 0.25
        base_tax = calculate_tax_slabs(20000000, regime)
        base_tax_after_rebate = base_tax * 1.15
        threshold = 20000000

    proposed_surcharge = computed_tax_after_rebate * surcharge_rate

    # Marginal Relief Calculation
    excess_income = taxable_income - threshold
    proposed_total_tax = computed_tax_after_rebate + proposed_surcharge
    max_total_tax_without_relief = base_tax_after_rebate + excess_income

    if proposed_total_tax > max_total_tax_without_relief:
        # Relief applies
        return max(0.0, float(max_total_tax_without_relief - computed_tax_after_rebate))
    
    return proposed_surcharge

def calculate_cess(tax_plus_surcharge):
    return tax_plus_surcharge * 0.04
