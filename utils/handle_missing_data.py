import openai
import pymongo
from tqdm import tqdm  # For progress bar

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client["Kompass_daad_university_data_master_en"]
collection = db["programs"]

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")  # Replace with your actual API key

def generate_missing_field(program_title, existing_fields):
    """Uses GPT-4 to generate missing values based on available data."""
    prompt = f"""
    You are an academic advisor specializing in university programs. Given a program title and some existing information, suggest a missing value.
    
    Program Title: {program_title}
    Existing Fields: {existing_fields}
    
    Please generate a meaningful completion for any missing fields (Area of Study, Focus, Target Group). Keep responses concise.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=50
        )
        return response['choices'][0]['message']['content'].strip()
    
    except Exception as e:
        print(f"Error in OpenAI API call: {e}")
        return None

# Fetch all programs from MongoDB
programs = list(collection.find())

# Iterate through each program and fill missing fields
for program in tqdm(programs, desc="Filling missing fields"):
    updated_fields = {}
    
    # Check for missing fields
    if "Area of Study" not in program or not program["Area of Study"]:
        generated_area_of_study = generate_missing_field(program["Program Title"], program)
        if generated_area_of_study:
            updated_fields["Area of Study"] = generated_area_of_study
    
    if "focus" not in program or not program["focus"]:
        generated_focus = generate_missing_field(program["Program Title"], program)
        if generated_focus:
            updated_fields["focus"] = generated_focus

    if "target group" not in program or not program["target group"]:
        generated_target_group = generate_missing_field(program["Program Title"], program)
        if generated_target_group:
            updated_fields["target group"] = generated_target_group

    # Update MongoDB only if there are new values
    if updated_fields:
        collection.update_one({"_id": program["_id"]}, {"$set": updated_fields})

print("✅ Missing fields successfully filled using OpenAI GPT-4!")
