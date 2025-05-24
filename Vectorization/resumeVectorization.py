"Resume Vectorization"

import os
import faiss
import numpy as np
import pandas as pd
import pickle  # To save FAISS index
import sqlite3
from tqdm import tqdm
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pydantic import BaseModel
from typing import List, Optional

# Set OpenAI API Key
os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# === Define Pydantic Models for Structured Extraction === #
class Education(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    graduation_date: Optional[str] = None

class WorkExperience(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[str] = None
    responsibilities: Optional[List[str]] = []

class ResumeSchema(BaseModel):
    education: Optional[List[Education]] = []
    work_experience: Optional[List[WorkExperience]] = []
    skills: Optional[List[str]] = []

# === Function to Load & Extract Text from Resume === #
def extract_resume_text(pdf_path: str) -> str:
    """Loads a PDF resume and extracts raw text using LangChain."""
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    full_text = " ".join([page.page_content for page in pages])
    return full_text

# === Function to Extract Relevant Information Using OpenAI === #
def extract_relevant_info(raw_text: str) -> str:
    """Uses OpenAI GPT-4 to extract structured resume information."""
    llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

    prompt_template = PromptTemplate(
        input_variables=["text"],
        template="""
        Extract structured key information from this resume:

        Education:
        - Degree, Institution, Graduation Year

        Work Experience:
        - Company, Position, Years of Experience, Responsibilities

        Skills:
        - List key skills

        Return ONLY the extracted information in structured format.
        
        Resume Text:
        {text}
        """
    )

    # Run the model with the prompt
    extraction_chain = prompt_template | llm
    result = extraction_chain.invoke({"text": raw_text})

    # ✅ Fix: Ensure the response is a string
    if hasattr(result, 'content'):
        extracted_text = result.content  # Extracts the text part
    else:
        extracted_text = str(result)  # Converts to string if needed

    # Debugging: Print extracted text
    print("\n🔍 Extracted Resume Data Before Vectorization:\n")
    print("-" * 80)
    print(extracted_text)
    print("-" * 80)

    return extracted_text.strip()

# === Function to Generate OpenAI Embeddings === #
def get_embedding(text: str):
    """Generates an embedding using OpenAI text-embedding-ada-002 model."""
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return np.array(response.data[0].embedding, dtype=np.float32)
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return None

# === Function to Store Resume Vectors in FAISS === #
def save_resume_to_faiss(resume_text, resume_embedding, resume_id):
    """Saves resume vector in FAISS for similarity search."""
    
    print(f"\n🔍 Debug: Storing Resume {resume_id} in FAISS...")

    # Load or create FAISS index
    try:
        with open("faiss_resumes.pkl", "rb") as f:
            index = pickle.load(f)
        print("✅ FAISS index loaded successfully.")
    except (FileNotFoundError, EOFError):
        print("⚠️ FAISS index not found. Creating a new one...")
        index = faiss.IndexFlatL2(resume_embedding.shape[0])  # L2 similarity

    # Ensure embedding has correct shape
    print(f"🔍 Debug: Resume embedding shape before adding: {resume_embedding.shape}")
    if len(resume_embedding.shape) == 1:
        resume_embedding = np.expand_dims(resume_embedding, axis=0)
        print(f"✅ Fixed embedding shape: {resume_embedding.shape}")

    # Try adding to FAISS
    try:
        index.add(resume_embedding)
        # Check the number of vectors in FAISS
        print(f"📌 FAISS now contains {index.ntotal} embeddings.")

        print("✅ Embedding added to FAISS.")
    except Exception as e:
        print(f"❌ FAISS Error: {e}")
        return

    # Save FAISS index
    try:
        with open("faiss_resumes.pkl", "wb") as f:
            pickle.dump(index, f)
        print("✅ FAISS index saved successfully.")
    except Exception as e:
        print(f"❌ Error saving FAISS index: {e}")
        return

    # Save metadata separately
    try:
        df = pd.DataFrame({"resume_id": [resume_id], "resume_text": [resume_text]})
        df.to_csv("resumes_metadata.csv", mode='a', header=False, index=False)
        print(f"✅ Metadata for {resume_id} stored in CSV.")
    except Exception as e:
        print(f"❌ Error saving resume metadata: {e}")



# === Function to Save Extracted Data to SQLite === #
def save_to_database(parsed_resume: ResumeSchema, resume_id: str):
    """Save the extracted resume data into an SQLite database."""
    conn = sqlite3.connect("resumes.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id TEXT PRIMARY KEY,
            education TEXT,
            work_experience TEXT,
            skills TEXT
        )
    """)

    # Convert structured data to strings
    education_str = str(parsed_resume.education) if parsed_resume.education else "N/A"
    work_experience_str = str(parsed_resume.work_experience) if parsed_resume.work_experience else "N/A"
    skills_str = ", ".join(parsed_resume.skills) if parsed_resume.skills else "N/A"

    cursor.execute("""
        INSERT INTO resumes (id, education, work_experience, skills)
        VALUES (?, ?, ?, ?)
    """, (resume_id, education_str, work_experience_str, skills_str))

    conn.commit()
    conn.close()
    print("\n✅ Resume data saved to database!")

# === Main Function to Run the Pipeline === #
def main():
    pdf_path = "resume.pdf"  # Replace with actual file path
    resume_id = "resume_001"  # Assign a unique resume ID

    raw_text = extract_resume_text(pdf_path)

    # Extract only relevant information using OpenAI
    extracted_text = extract_relevant_info(raw_text)

    # Ensure we don't store garbage
    if not extracted_text.strip():
        print("\n❌ Extraction Failed: Resume text is empty or invalid.")
        return
    
    # Generate embedding
    resume_embedding = get_embedding(extracted_text)
    print(resume_embedding)

    if resume_embedding is not None:
        # Save to FAISS
        save_resume_to_faiss(extracted_text, resume_embedding, resume_id)

        # Save structured resume data to SQLite
        parsed_resume = ResumeSchema()  # We are no longer storing personal info
        #save_to_database(parsed_resume, resume_id)

if __name__ == "__main__":
    main()
