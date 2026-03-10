#!/usr/bin/env python3
"""
Create Advanced Store Dataset for Shop Assist RAG System
Generates comprehensive retail data with predictive analytics, recommendations, and voice agent support.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def create_advanced_store_dataset():
    """Create a comprehensive advanced store dataset with predictive analytics, recommendations, and voice agent support."""
    # Set random seed for reproducibility
    np.random.seed(42)
    random.seed(42)
    # ...existing code for categories, stores, festive_seasons, occasions, materials, colors, patterns...
    categories = {
        "Men's Clothing": ["Formal Shirts", "Casual Shirts", "Trousers", "Blazers", "T-Shirts", "Jeans", "Kurtas"],
        "Women's Clothing": ["Dresses", "Tops", "Blouses", "Skirts", "Jeans", "Coats", "Sarees", "Kurtis"],
        "Footwear": ["Formal Shoes", "Casual Shoes", "Sandals", "Boots", "Sports Shoes", "Heels"],
        "Accessories": ["Bags", "Belts", "Watches", "Jewelry", "Scarves", "Sunglasses", "Wallets"],
        "Kids & Teens": ["Boys Clothing", "Girls Clothing", "Kids Footwear", "School Uniforms"]
    }
    stores = [
        # {"name": "Shop Assist - Inorbit Mall", "location": "Mumbai", "area": "Malad West", "type": "Premium Mall", "rating": 4.5, "footfall": "High"},
        {"name": "Shop Assist - GVK One Mall", "location": "Hyderabad", "area": "Kukatpally", "type": "Premium Mall", "rating": 4.3, "footfall": "High"},
        {"name": "Shop Assist - Kukatpally", "location": "Hyderabad", "area": "Kukatpally", "type": "Standalone", "rating": 4.1, "footfall": "Medium"},
        {"name": "Shop Assist - Forum Sujana Mall", "location": "Hyderabad", "area": "Kukatpally", "type": "Mall", "rating": 4.2, "footfall": "Medium"},
        # {"name": "Shop Assist - Phoenix MarketCity", "location": "Mumbai", "area": "Kurla West", "type": "Premium Mall", "rating": 4.4, "footfall": "High"},
        # {"name": "Shop Assist - DLF Cyber City", "location": "Delhi", "area": "Gurgaon", "type": "Corporate Hub", "rating": 4.6, "footfall": "Very High"},
        # {"name": "Shop Assist - Select Citywalk", "location": "Delhi", "area": "Saket", "type": "Premium Mall", "rating": 4.7, "footfall": "Very High"},
        # {"name": "Shop Assist - UB City", "location": "Bangalore", "area": "Central", "type": "Luxury Mall", "rating": 4.8, "footfall": "High"},
        # {"name": "Shop Assist - Phoenix Mall", "location": "Bangalore", "area": "Whitefield", "type": "Premium Mall", "rating": 4.5, "footfall": "High"},
        # {"name": "Shop Assist - VR Mall", "location": "Chennai", "area": "Anna Nagar", "type": "Premium Mall", "rating": 4.3, "footfall": "Medium"}
    ]
    festive_seasons = ["Diwali", "Holi", "Eid", "Christmas", "New Year", "Wedding Season", "Summer Sale", "Winter Collection", "Monsoon Ready", "Spring Collection"]
    occasions = ["Formal Office", "Casual Outing", "Wedding", "Party", "Travel", "Sports", "Daily Wear", "Special Occasion", "Festival", "Business Meeting"]
    materials = ["Cotton", "Polyester", "Silk", "Linen", "Denim", "Wool", "Blend", "Rayon", "Crepe", "Georgette"]
    colors = ["Navy Blue", "Black", "White", "Red", "Green", "Yellow", "Pink", "Purple", "Orange", "Brown", "Grey", "Beige"]
    patterns = ["Solid", "Striped", "Floral", "Geometric", "Abstract", "Polka Dots", "Checks", "Paisley", "Animal Print", "Tie & Dye"]
    products = []
    product_id = 1
    for category, subcategories in categories.items():
        for subcategory in subcategories:
            for _ in range(8):
                material = random.choice(materials)
                color = random.choice(colors)
                pattern = random.choice(patterns)
                size = random.choice(["XS", "S", "M", "L", "XL", "XXL", "Free Size"])
                rating = round(random.uniform(3.5, 5.0), 1)
                review_count = random.randint(10, 500)
                purchase_count = random.randint(5, 200)
                view_count = random.randint(50, 1000)
                availability = random.choice(["In Stock", "Limited Stock", "Out of Stock", "Pre-order"])
                stock_quantity = random.randint(0, 100) if availability != "Out of Stock" else 0
                base_price = random.randint(500, 5000)
                discount_percent = random.choice([0, 10, 15, 20, 25, 30, 40, 50])
                discounted_price = base_price * (1 - discount_percent / 100)
                festive_tag = random.choice(festive_seasons + [""])
                occasion_tags = random.sample(occasions, random.randint(1, 3))
                store = random.choice(stores)
                seasonal_availability = random.choice(["All Year", "Summer", "Winter", "Monsoon", "Spring", "Festival Season"])
                features = []
                if "Formal" in subcategory:
                    features.extend(["Wrinkle Resistant", "Easy Iron", "Breathable"])
                if "Cotton" in material:
                    features.extend(["Natural Fiber", "Comfortable", "Absorbent"])
                if "Premium" in store["type"]:
                    features.extend(["Premium Quality", "Exclusive Design"])
                target_audience = random.choice(["Young Professionals", "Students", "Business Executives", "Fashion Enthusiasts", "Casual Wearers"])
                style_preference = random.choice(["Classic", "Modern", "Trendy", "Minimalist", "Bold", "Elegant"])
                reorder_level = max(5, stock_quantity // 4)
                lead_time_days = random.randint(1, 14)
                supplier_rating = round(random.uniform(3.0, 5.0), 1)
                # Predictive analytics
                sales_history = [random.randint(0, 10) for _ in range(30)]
                predicted_demand = int(np.mean(sales_history) * random.uniform(1.05, 1.25))
                forecasted_stockout = stock_quantity < predicted_demand
                sales_projection = int(np.mean(sales_history) * 30)
                # Recommendation system
                user_views = random.randint(100, 2000)
                user_clicks = random.randint(20, user_views)
                user_purchases = random.randint(5, user_clicks)
                similarity_score = round(random.uniform(0.5, 1.0), 2)
                recommended_flag = random.choice([True, False])
                collaborative_group = random.choice(["A", "B", "C", "D"])
                # Voice agent
                sample_utterances = [
                    f"Show me {color} {subcategory}s",
                    f"Find {subcategory} for {festive_tag if festive_tag else 'any occasion'}",
                    f"What are the best deals on {subcategory}?"
                ]
                intent_tags = ["search_product", "find_deal", "filter_by_festive"]
                last_query = sample_utterances[0]
                user_profile = target_audience
                product = {
                    "Product_ID": product_id,
                    "Product_Category": category,
                    "Product_Subcategory": subcategory,
                    "Product_Name": f"{color} {pattern} {subcategory}",
                    "Material": material,
                    "Color": color,
                    "Pattern": pattern,
                    "Size": size,
                    "Base_Price": base_price,
                    "Discount_Percent": discount_percent,
                    "Discounted_Price": round(discounted_price, 2),
                    "Availability": availability,
                    "Stock_Quantity": stock_quantity,
                    "Reorder_Level": reorder_level,
                    "Lead_Time_Days": lead_time_days,
                    "Store_Name": store["name"],
                    "Store_Location": store["location"],
                    "Store_Area": store["area"],
                    "Store_Type": store["type"],
                    "Store_Rating": store["rating"],
                    "Store_Footfall": store["footfall"],
                    "Customer_Rating": rating,
                    "Review_Count": review_count,
                    "Purchase_Count": purchase_count,
                    "View_Count": view_count,
                    "Festive_Season": festive_tag,
                    "Occasion_Tags": ", ".join(occasion_tags),
                    "Seasonal_Availability": seasonal_availability,
                    "Product_Features": ", ".join(features),
                    "Target_Audience": target_audience,
                    "Style_Preference": style_preference,
                    "Supplier_Rating": supplier_rating,
                    "Last_Updated": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
                    "Trending_Score": round(random.uniform(0.1, 1.0), 2),
                    "Sustainability_Score": round(random.uniform(0.3, 1.0), 2),
                    "Return_Rate": round(random.uniform(0.01, 0.15), 3),
                    "Warranty_Period": random.choice([0, 30, 90, 180, 365]),
                    # Predictive analytics fields
                    "Sales_History": sales_history,
                    "Predicted_Demand": predicted_demand,
                    "Forecasted_Stockout": forecasted_stockout,
                    "Sales_Projection": sales_projection,
                    # Recommendation system fields
                    "User_Views": user_views,
                    "User_Clicks": user_clicks,
                    "User_Purchases": user_purchases,
                    "Similarity_Score": similarity_score,
                    "Recommended_Flag": recommended_flag,
                    "Collaborative_Group": collaborative_group,
                    # Voice agent fields
                    "Sample_Utterances": sample_utterances,
                    "Intent_Tags": intent_tags,
                    # Conversational context
                    "Last_Query": last_query,
                    "User_Profile": user_profile
                }
                products.append(product)
                product_id += 1
    df = pd.DataFrame(products)
    df["Price_Range"] = df["Base_Price"].apply(lambda x: "Budget" if x < 1000 else "Mid-Range" if x < 2500 else "Premium" if x < 4000 else "Luxury")
    df["Stock_Status"] = df.apply(lambda row: "Critical" if row["Stock_Quantity"] <= row["Reorder_Level"] else "Low" if row["Stock_Quantity"] <= row["Reorder_Level"] * 2 else "Good" if row["Stock_Quantity"] > 20 else "Limited", axis=1)
    df["Popularity_Score"] = df.apply(lambda row: (row["Customer_Rating"] * 0.4 + row["Purchase_Count"] / 200 * 0.3 + row["View_Count"] / 1000 * 0.3), axis=1)
    df["Profit_Margin"] = df.apply(lambda row: round((row["Base_Price"] - row["Discounted_Price"]) / row["Base_Price"] * 100, 2), axis=1)
    df = df.sort_values("Popularity_Score", ascending=False).reset_index(drop=True)
    return df

def create_store_analytics():
    """Create store performance analytics data."""
    stores_analytics = [
        {
            "Store_Name": "Shop Assist - Inorbit Mall",
            "Location": "Mumbai",
            "Monthly_Revenue": 850000,
            "Customer_Footfall": 2500,
            "Conversion_Rate": 0.28,
            "Average_Transaction_Value": 3400,
            "Customer_Satisfaction": 4.5,
            "Return_Rate": 0.08,
            "Top_Category": "Men's Clothing",
            "Peak_Hours": "2 PM - 8 PM",
            "Seasonal_Peak": "Diwali, Christmas",
            "Staff_Count": 12,
            "Operating_Hours": "10 AM - 10 PM"
        },
        {
            "Store_Name": "Shop Assist - GVK One Mall",
            "Location": "Mumbai",
            "Monthly_Revenue": 720000,
            "Customer_Footfall": 2200,
            "Conversion_Rate": 0.25,
            "Average_Transaction_Value": 3200,
            "Customer_Satisfaction": 4.3,
            "Return_Rate": 0.09,
            "Top_Category": "Women's Clothing",
            "Peak_Hours": "3 PM - 9 PM",
            "Seasonal_Peak": "Wedding Season, Summer",
            "Staff_Count": 10,
            "Operating_Hours": "10 AM - 10 PM"
        },
        {
            "Store_Name": "Shop Assist - DLF Cyber City",
            "Location": "Delhi",
            "Monthly_Revenue": 950000,
            "Customer_Footfall": 3000,
            "Conversion_Rate": 0.32,
            "Average_Transaction_Value": 3800,
            "Customer_Satisfaction": 4.6,
            "Return_Rate": 0.06,
            "Top_Category": "Formal Wear",
            "Peak_Hours": "12 PM - 7 PM",
            "Seasonal_Peak": "All Year",
            "Staff_Count": 15,
            "Operating_Hours": "9 AM - 9 PM"
        }
    ]
    return pd.DataFrame(stores_analytics)

def create_customer_preferences():
    """Create customer preference and behavior data."""
    
    customer_data = [
        {
            "Customer_Segment": "Young Professionals (25-35)",
            "Preferred_Categories": "Formal Shirts, Blazers, Trousers",
            "Price_Sensitivity": "Medium",
            "Brand_Loyalty": "High",
            "Online_Shopping": "Yes",
            "Seasonal_Preferences": "All Year",
            "Occasion_Focus": "Office, Business Meetings",
            "Average_Purchase_Frequency": "Monthly",
            "Preferred_Colors": "Navy Blue, Black, White",
            "Size_Preference": "M, L"
        },
        {
            "Customer_Segment": "Fashion Enthusiasts (18-30)",
            "Preferred_Categories": "Dresses, Tops, Accessories",
            "Price_Sensitivity": "Low",
            "Brand_Loyalty": "Medium",
            "Online_Shopping": "Yes",
            "Seasonal_Preferences": "Trend-based",
            "Occasion_Focus": "Parties, Social Events",
            "Average_Purchase_Frequency": "Bi-weekly",
            "Preferred_Colors": "Bright Colors, Pastels",
            "Size_Preference": "S, M"
        },
        {
            "Customer_Segment": "Business Executives (35-50)",
            "Preferred_Categories": "Premium Formal Wear, Accessories",
            "Price_Sensitivity": "Low",
            "Brand_Loyalty": "Very High",
            "Online_Shopping": "Sometimes",
            "Seasonal_Preferences": "All Year",
            "Occasion_Focus": "Business, Formal Events",
            "Average_Purchase_Frequency": "Quarterly",
            "Preferred_Colors": "Classic Colors",
            "Size_Preference": "L, XL"
        }
    ]
    
    return pd.DataFrame(customer_data)

def main():
    """Main function to create and save the advanced dataset."""
    
    print("🚀 Creating Advanced Store Dataset for Shop Assist RAG System...")
    
    # Create main product dataset
    products_df = create_advanced_store_dataset()
    print(f"✅ Created {len(products_df)} product records with advanced features")
    
    # Create store analytics
    stores_df = create_store_analytics()
    print(f"✅ Created {len(stores_df)} store analytics records")
    
    # Create customer preferences
    customers_df = create_customer_preferences()
    print(f"✅ Created {len(customers_df)} customer preference records")
    
    # Save to Excel with multiple sheets
    output_file = "data/documents/advanced_shop_assist_store_data.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        products_df.to_excel(writer, sheet_name='Products', index=False)
        stores_df.to_excel(writer, sheet_name='Store_Analytics', index=False)
        customers_df.to_excel(writer, sheet_name='Customer_Preferences', index=False)
    
    print(f"💾 Dataset saved to: {output_file}")
    
    # Display sample data
    print("\n📊 Sample Product Data:")
    print(products_df[["Product_Category", "Product_Subcategory", "Product_Name", "Customer_Rating", "Purchase_Count", "Festive_Season", "Popularity_Score"]].head(10))
    
    print("\n📊 Sample Store Analytics:")
    print(stores_df[["Store_Name", "Location", "Monthly_Revenue", "Customer_Footfall", "Conversion_Rate"]].head())
    
    print("\n📊 Sample Customer Preferences:")
    print(customers_df[["Customer_Segment", "Preferred_Categories", "Price_Sensitivity", "Brand_Loyalty"]].head())
    
    print("\n🎯 Advanced Features Added:")
    print("• Product ratings and reviews")
    print("• Purchase history and popularity scores")
    print("• Festive season and occasion tags")
    print("• Store performance analytics")
    print("• Customer segmentation and preferences")
    print("• Material, color, and pattern details")
    print("• Seasonal availability and trending scores")
    print("• Inventory management metrics")
    print("• Sustainability and warranty information")
    print("• Price ranges and profit margins")
    
    print(f"\n🎉 Your RAG system now has {len(products_df)} rich product records!")
    print("Ready for advanced queries like:")
    print("• 'Show me most rated products'")
    print("• 'Find festive collection for Diwali'")
    print("• 'What's trending this season?'")
    print("• 'Best products for business meetings'")
    print("• 'Most purchased items in Mumbai stores'")

if __name__ == "__main__":
    main() 