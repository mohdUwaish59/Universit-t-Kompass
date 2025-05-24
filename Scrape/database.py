from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["Kompass_daad_university_data_master_en"]  # Replace with your actual database name

# Get all collections
collections = db.list_collection_names()

# Dictionary to store schema details
schema_info = {}

for collection_name in collections:
    collection = db[collection_name]
    
    # Fetch a larger sample of documents (increase limit if needed)
    sample_documents = collection.find().limit(100)  # Adjust the limit as required
    
    field_set = set()
    
    for doc in sample_documents:
        field_set.update(doc.keys())
    
    schema_info[collection_name] = sorted(field_set)  # Sort for better readability

# Display schema details
for collection, fields in schema_info.items():
    print(f"\nCollection: {collection}")
    print("Schema Fields:", fields)


