import os
from dotenv import load_dotenv
from supabase import create_client, Client
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize the MCP server instance
mcp = FastMCP("Coffee Barista MCP")

@mcp.tool()
def get_recent_shots(limit: int = 5) -> str:
    """
    Fetch the user's most recent espresso and coffee shots from Supabase.
    Use this tool to analyze trends, history, or extraction parameters.
    """
    try:
        response = supabase.table("shots").select("*").order("created_at", desc=True).limit(limit).execute()
        data = response.data
        
        if not data:
            return "No coffee shots found in the database."
        
        result = ["Recent coffee shots:\n"]
        for shot in data:
            result.append(
                f"- Date: {shot.get('created_at')} | Method: {shot.get('brew_method')} | "
                f"Dose: {shot.get('dose')}g | Yield: {shot.get('yield')}g | "
                f"Time: {shot.get('extraction_time')}s | Score: {shot.get('overall_score')}/10"
            )
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Database error: {str(e)}"

if __name__ == "__main__":
    # Run the server via stdio (standard MCP transport)
    mcp.run()


@mcp.tool()
def analyze_best_value_coffees() -> str:
    """
    Analyzes all coffee beans to find the best Value for Money (VFM).
    Calculates average user scores, price per 100g, and identifies the best brew methods for each bean.
    Use this tool when the user asks for recommendations, the best coffee, or price/value analysis.
    """
    try:
        # 1. Fetch beans and shots from Supabase
        beans_response = supabase.table("beans").select("id, roaster, origin, price_paid, weight_grams").execute()
        shots_response = supabase.table("shots").select("bean_id, overall_score, brew_method").execute()
        
        beans = beans_response.data
        shots = [s for s in shots_response.data if s.get("overall_score") is not None and s.get("bean_id") is not None]

        if not beans or not shots:
            return "Not enough data to perform VFM analysis."

        # 2. Aggregate shots by bean_id
        bean_stats = {}
        for shot in shots:
            b_id = shot["bean_id"]
            score = shot["overall_score"]
            method = shot["brew_method"]

            if b_id not in bean_stats:
                bean_stats[b_id] = {"scores": [], "methods": {}}
            
            bean_stats[b_id]["scores"].append(score)
            
            if method not in bean_stats[b_id]["methods"]:
                bean_stats[b_id]["methods"][method] = []
            bean_stats[b_id]["methods"][method].append(score)

        # 3. Calculate metrics and format the report
        result = ["☕ Coffee Value For Money (VFM) & Brew Analysis:\n"]
        
        for bean in beans:
            b_id = bean.get("id")
            stats = bean_stats.get(b_id)
            
            if not stats:
                continue # Skip beans with no logged shots

            avg_score = sum(stats["scores"]) / len(stats["scores"])
            
            # Calculate the most successful brew method
            method_avgs = {m: sum(s)/len(s) for m, s in stats["methods"].items()}
            best_method = max(method_avgs, key=method_avgs.get)

            price = bean.get("price_paid")
            weight = bean.get("weight_grams")
            
            # Calculate VFM if price and weight exist
            if price and weight and float(weight) > 0:
                price_per_100g = (float(price) / float(weight)) * 100
                vfm_index = avg_score / price_per_100g if price_per_100g > 0 else 0
                cost_str = f"${price_per_100g:.2f} per 100g | VFM Index: {vfm_index:.2f}"
            else:
                cost_str = "Price/Weight data missing"

            result.append(
                f"🔹 {bean.get('roaster')} - {bean.get('origin')}\n"
                f"   • Overall Score: {avg_score:.1f}/10 (based on {len(stats['scores'])} shots)\n"
                f"   • Value: {cost_str}\n"
                f"   • Best Method: {best_method} (Avg: {method_avgs[best_method]:.1f}/10)\n"
            )

        return "\n".join(result)

    except Exception as e:
        return f"Error analyzing beans: {str(e)}"