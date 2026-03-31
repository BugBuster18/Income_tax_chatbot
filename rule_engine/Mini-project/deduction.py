def validate_80D(data):
    errors = []

    deductions = data.get("deductions", {})
    age = data.get("age", 30)

    total_80D = (
        deductions.get("health_insurance_self", 0) +
        deductions.get("health_insurance_family", 0) +
        deductions.get("health_insurance_parents", 0)
    )

    # Decide limit
    if age >= 60:
        limit = 50000
    else:
        limit = 25000

    if total_80D > limit:
        errors.append("80D_LIMIT_EXCEEDED")

    return errors