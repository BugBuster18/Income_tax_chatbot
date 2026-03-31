from z3 import Solver, Int, String, If, And, Or, Not, unsat
from error_codes import ErrorCodes

def validate_regime(data):
    """
    Validation logic using Z3 Solver for regime-based constraints.
    Checks if there's any invalid combination of regime and claimed deductions/exemptions.
    """
    errors = []
    
    # Initialize Z3 Solver
    s = Solver()

    # Z3 Variables
    # 0 implies 'old', 1 implies 'new'
    regime_val = (data.get("regime") or "new").lower()
    regime_enum = 1 if regime_val == "new" else 0
    regime_z3 = Int("regime")
    
    deductions = data.get("deductions") or {}
    exemptions = data.get("exemptions") or {}

    # Extract boolean values whether deductions/exemptions are claimed
    # 1 implies claimed, 0 implies not claimed
    # Section 80C
    has_80c = 1 if "80C" in deductions and deductions["80C"] else 0
    z3_80c = Int("80c")
    
    # Section 80D
    has_80d = 1 if "80D" in deductions and deductions["80D"] else 0
    z3_80d = Int("80d")

    # NPS 80CCD(1B)
    has_80ccd1b = 1 if deductions.get("NPS", {}).get("employee_80ccd1b", 0) > 0 else 0
    z3_80ccd1b = Int("80ccd1b")
    
    # HRA
    has_hra = 1 if "HRA" in exemptions and exemptions["HRA"] else 0
    z3_hra = Int("hra")

    # Add Facts to Solver
    s.add(regime_z3 == regime_enum)
    s.add(z3_80c == has_80c)
    s.add(z3_80d == has_80d)
    s.add(z3_80ccd1b == has_80ccd1b)
    s.add(z3_hra == has_hra)

    # RULE CONSTRAINTS
    # If Regime is New (1), then 80C, 80D, 80CCD(1B), and HRA must be 0
    # Equivalently: if regime_z3 == 1, then z3_80c == 0 (else violation)
    
    # Check 80C Constraint
    s.push()
    s.add(And(regime_z3 == 1, z3_80c == 1))
    if s.check() != unsat:
        errors.append(ErrorCodes.NOT_ALLOWED_IN_NEW_REGIME_80C)
    s.pop()

    # Check 80D Constraint
    s.push()
    s.add(And(regime_z3 == 1, z3_80d == 1))
    if s.check() != unsat:
        errors.append(ErrorCodes.NOT_ALLOWED_IN_NEW_REGIME_80D)
    s.pop()

    # Check 80CCD(1B) Constraint
    s.push()
    s.add(And(regime_z3 == 1, z3_80ccd1b == 1))
    if s.check() != unsat:
        errors.append(ErrorCodes.NOT_ALLOWED_IN_NEW_REGIME_80CCD1B)
    s.pop()

    # Check HRA Constraint
    s.push()
    s.add(And(regime_z3 == 1, z3_hra == 1))
    if s.check() != unsat:
        errors.append(ErrorCodes.NOT_ALLOWED_IN_NEW_REGIME_HRA)
    s.pop()

    return list(set(errors)) # Deduplicate
