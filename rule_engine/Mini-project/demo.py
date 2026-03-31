import json
from validator import validate_all

def main():
    print("=== INCOME TAX RULE ENGINE DEMO ===")
    
    # TEST CASE 1: Valid Old Regime
    user_data_1 = {
        "income": 1200000,
        "basic_salary": 600000,
        "da": 0,
        "age": 30,
        "regime": "old",
        "exemptions": {
            "HRA": {
                "hra_received": 150000,
                "rent_paid": 180000,
                "is_metro": True
            }
        },
        "deductions": {
            "80C": {
                "ppf": 100000,
                "elss": 60000 # Exceeds 1.5L limit
            },
            "80D": {
                "health_insurance_self_family": 30000 # Exceeds 25k limit
            },
            "standard_deduction": 50000
        }
    }

    print("\n--- Test Case 1: Old Regime with Limits Exceeded ---")
    print("Input Data:")
    print(json.dumps(user_data_1, indent=2))
    
    result_1 = validate_all(user_data_1)
    
    print("\nOutput Data:")
    print(json.dumps(result_1, indent=2))


    # TEST CASE 2: Invalid Regime Selection (Regime Clash via Z3)
    user_data_2 = {
        "income": 1500000,
        "age": 35,
        "regime": "new",
        "deductions": {
            "80C": {
                "elss": 50000 
            },
            "80D": {
                "health_insurance_self_family": 20000 
            },
            "standard_deduction": 75000
        }
    }

    print("\n--- Test Case 2: New Regime Claiming 80C & 80D (Z3 Clash) ---")
    print("Input Data:")
    print(json.dumps(user_data_2, indent=2))
    
    result_2 = validate_all(user_data_2)
    
    print("\nOutput Data:")
    print(json.dumps(result_2, indent=2))

    # TEST CASE 3: Fully Valid Old Regime
    user_data_3 = {
        "income": 800000,
        "basic_salary": 400000,
        "da": 0,
        "age": 30,
        "regime": "old",
        "exemptions": {},
        "deductions": {
            "80C": {
                "ppf": 100000
            },
            "80D": {
                "health_insurance_self_family": 15000 
            },
            "standard_deduction": 50000
        }
    }

    print("\n--- Test Case 3: Fully Valid Old Regime (Within Limits) ---")
    print("Input Data:")
    print(json.dumps(user_data_3, indent=2))
    
    result_3 = validate_all(user_data_3)
    
    print("\nOutput Data:")
    print(json.dumps(result_3, indent=2))


if __name__ == "__main__":
    main()
