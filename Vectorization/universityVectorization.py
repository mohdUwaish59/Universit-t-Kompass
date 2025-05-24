import faiss
import numpy as np
import pandas as pd
import pymongo
import pickle  # To save FAISS index
from tqdm import tqdm
import openai
import os

# Set OpenAI API Key
os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]

# Connect to MongoDB
client = pymongo.MongoClient("mongodb+srv://muwaish5:yzrmHtwsQSQM9mHU@cluster0.olcx7kr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") 
db = client["Kompass_daad_university_data_master_en"]
collection = db["programs"]

# Load all programs into a Pandas DataFrame
programs = list(collection.find({}, {
    "_id": 1, 
    "University Name": 1, 
    "Program Title": 1, 
    "Area of Study": 1, 
    "Focus": 1, 
    "Target Group": 1
}))
df = pd.DataFrame(programs)

# Function to safely convert arrays to strings
def convert_array_to_string(value):
    if isinstance(value, list):
        return ", ".join(value) if value else "Unknown"
    elif isinstance(value, dict):
        return "Unknown"
    elif pd.isnull(value) or str(value).strip() == "":
        return "Unknown"
    return str(value)

# Convert relevant fields to strings
for field in ["Area of Study", "Focus", "Target Group"]:
    if field in df.columns:
        df[field] = df[field].apply(convert_array_to_string)

# Create a combined text column for embedding
df["combined_text"] = df["Program Title"] + " | " + df["Area of Study"] + " | " + df["Focus"] + " | " + df["Target Group"]

# Function to generate OpenAI embeddings
def get_openai_embedding(text):
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return np.array(response.data[0].embedding, dtype=np.float32)
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return None

# Generate embeddings using OpenAI
print("\n🔍 Generating university embeddings with OpenAI...")
df["embedding"] = df["combined_text"].apply(get_openai_embedding)

# Drop rows where embedding generation failed
df = df.dropna(subset=["embedding"]).reset_index(drop=True)

# Convert embeddings to numpy array
embeddings = np.vstack(df["embedding"].values)

# Create FAISS index
dimension = embeddings.shape[1]  # Should be 1536
index = faiss.IndexFlatL2(dimension)  # L2 distance
index.add(embeddings)

# Save FAISS index to a file
with open("faiss_universities.pkl", "wb") as f:
    pickle.dump(index, f)

# Save processed university data
df.to_csv("university_programs.csv", index=False)

print(f"✅ OpenAI embeddings stored in FAISS and saved to disk! ({index.ntotal} university programs)")
