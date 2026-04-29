from server import get_recent_shots, analyze_best_value_coffees

def run_tests():
    print("🔌 Testing connection to Supabase...\n")
    
    print("--- 1. Testing get_recent_shots(3) ---")
    recent = get_recent_shots(limit=3)
    print(recent)
    
    print("\n" + "="*40 + "\n")
    
    print("--- 2. Testing analyze_best_value_coffees() ---")
    analysis = analyze_best_value_coffees()
    print(analysis)

if __name__ == "__main__":
    run_tests()