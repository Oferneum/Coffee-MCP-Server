import os
import random
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def seed_database():
    print("🌱 Seeding database with mock data...")

    mock_beans = [
        {"roaster": "Onyx Coffee Lab", "origin": "Ethiopia Worka", "price_paid": 22.0, "weight_grams": 250, "is_active": True, "roast_date": "2026-04-15"},
        {"roaster": "Sey Coffee", "origin": "Colombia Chiroso", "price_paid": 26.0, "weight_grams": 250, "is_active": True, "roast_date": "2026-04-20"},
        {"roaster": "Mae Cafe", "origin": "Brazil Cerrado", "price_paid": 14.0, "weight_grams": 250, "is_active": True, "roast_date": "2026-04-10"}
    ]
    
    print("Inserting beans...")
    beans_res = supabase.table("beans").insert(mock_beans).execute()
    inserted_beans = beans_res.data
    
    if not inserted_beans:
        print("❌ Failed to insert beans. Check your connection or permissions.")
        return

    bean_ids = [bean["id"] for bean in inserted_beans]
    
    mock_shots = []
    brew_methods = ["Espresso", "V60", "FrenchPress"]
    
    for _ in range(20):
        method = random.choice(brew_methods)
        dose = round(random.uniform(15.0, 20.0), 1)
        
       
        if method == "Espresso":
            yield_g = round(dose * random.uniform(1.8, 2.5), 1)
            time = random.randint(22, 35)
        else:
            yield_g = round(dose * 15, 1) 
            time = random.randint(120, 210)
            
        score = random.randint(5, 10) 
        
        mock_shots.append({
            "bean_id": random.choice(bean_ids),
            "brew_method": method,
            "dose": dose,
            "yield": yield_g,
            "extraction_time": time,
            "brew_temp": random.choice([92.0, 93.0, 94.0, 95.0]),
            "overall_score": score,
            "has_milk": random.choice([True, False]),
            "grind_setting": str(random.randint(10, 20))
        })
        
    print(f"Inserting {len(mock_shots)} shots...")
    supabase.table("shots").insert(mock_shots).execute()
    
    print("✅ Database seeded successfully! Your mock data is ready.")

if __name__ == "__main__":
    seed_database()