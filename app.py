import streamlit as st
import os
import faiss
import numpy as np
import pandas as pd
import pickle
import openai
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from PyPDF2 import PdfReader
import time
from dotenv import load_dotenv
from pymongo import MongoClient
import random
import re

# Load environment variables
load_dotenv()
MONGO_URI = st.secrets["MONGO_URI"]

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Database for contacts and deadlines
db_contacts = client["Kompass_daad_university_data_master_en"]
collection_contacts = db_contacts["programs"]
# Set OpenAI API Key
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Load FAISS index and university metadata
faiss_index_path = "data/faiss_universities.pkl"
metadata_path = "data/merged_program_data.csv"


# Load FAISS index
if os.path.exists(faiss_index_path):
    with st.spinner("🔄 Loading FAISS index..."):
        with open(faiss_index_path, "rb") as f:
            index = pickle.load(f)
        #st.success(f"✅ FAISS index loaded. Total programs: {index.ntotal}")
else:
    st.error("❌ FAISS index not found! Run university_vectorization.py first.")

# Load university metadata
if os.path.exists(metadata_path):
    with st.spinner("📂 Loading university metadata..."):
        university_metadata = pd.read_csv(metadata_path)
        #st.success(f"✅ Loaded {len(university_metadata)} university programs.")
        st.success(f"✅ Loaded all universities metadata.")
else:
    st.error("❌ University metadata CSV not found!")

# Helper Function: Display Contact Details
def display_contact(contact):
    """Displays contact details in Streamlit."""
    if contact.get("Name"):
        st.markdown(f"👤 **Name:** {contact['Name']}")
    if contact.get("Address"):
        st.markdown(f"📍 **Address:** {contact['Address']}, {contact.get('City', 'N/A')}, {contact.get('Postal Code', 'N/A')}")
    if contact.get("Phone"):
        st.markdown(f"📞 **Phone:** {contact['Phone']}")
    if contact.get("Fax"):
        st.markdown(f"📠 **Fax:** {contact['Fax']}")
    if contact.get("Email"):
        st.markdown(f"📧 **Email:** [{contact['Email']}]({contact['Email']})")
    if contact.get("Website"):
        st.markdown(f"🌐 **Website:** [{contact['Website']}]({contact['Website']})")

# Helper Function: Display Application Deadlines
def display_deadlines(deadlines):
    """Displays application deadlines in Streamlit."""
    for semester, deadline_list in deadlines.items():
        st.markdown(f"### {semester}")
        for deadline in deadline_list:
            st.markdown(f"- **{deadline.get('Type', 'Deadline')}**: {deadline.get('Dates', 'N/A')}")

# Existing Functions (Unchanged)
def extract_resume_text(uploaded_file):
    """Extracts text from an uploaded PDF resume."""
    with st.spinner("📄 Extracting raw text from resume..."):
        text = ""
        pdf_reader = PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            text += page.extract_text() + " "
        time.sleep(1)
    return text.strip()


def extract_relevant_info(raw_text):
    """Uses OpenAI GPT-4 to extract structured resume information."""
    with st.spinner("🧠 Extracting relevant resume details using AI..."):
        llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

        prompt_template = PromptTemplate(
            input_variables=["text"],
            template="""
            Extract structured key information from this resume:
            Name:
            Email:
            Education:
            - Degree, Institution, Graduation Year

            Work Experience:
            - Company, Position, Years of Experience, Responsibilities

            Skills:
            - List key skills

            Return ONLY the extracted information in structured format.
            
            If you find that the text is not from a resume or C.V., then please return this response: "This is not a resume."
            
            Resume Text:
            {text}
            """
        )

        extraction_chain = prompt_template | llm
        result = extraction_chain.invoke({"text": raw_text})
        time.sleep(1)

    extracted_text = result.content if hasattr(result, 'content') else str(result)
    if str(extracted_text).strip() == "This is not a resume.":
        st.error("❌ The uploaded file does not appear to be a resume. Please upload a valid resume.")
        return None

    # Debugging Output
    st.subheader("🔍 Extracted Resume Data Before Vectorization")
    st.text_area("Extracted Sections:", extracted_text, height=200)

    return extracted_text.strip()

def extract_name_email(text):
    """Extracts name and email from the resume text."""
    # Regular expressions for name and email
    name_pattern = r"(?i)Name:\s*(.+)"
    email_pattern = r"(?i)Email:\s*([\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,})"

    # Extract name
    name_match = re.search(name_pattern, text)
    name = name_match.group(1).strip() if name_match else "Name not found"

    # Extract email
    email_match = re.search(email_pattern, text)
    email = email_match.group(1).strip() if email_match else "Email not found"
    
    # Connect to MongoDB
    db = client["Kompass_Users"]
    collection = db["users_name_email"]

    # Prepare the document
    user_data = {
        "name": name,
        "email": email
    }

    # Insert the document into the collection
    result = collection.insert_one(user_data)

    return name, email

def get_embedding(text):
    """Generates an embedding using OpenAI text-embedding-ada-002 model."""
    with st.spinner("🔢 Generating AI embeddings for resume..."):
        try:
            response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            time.sleep(1)
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            st.error(f"❌ Error generating embedding: {e}")
            return None
        
def get_university_portal_link(program_link):
    """Fetch course detail link of the university portal from MongoDB using the Program Link."""
    course_link_entry = collection_contacts.find_one({"Program Link": program_link}, {"Course Detail Link": 1})
    return course_link_entry.get("Course Detail Link", {}) if course_link_entry else []

def get_contact_details(program_link):
    """Fetch contact details from MongoDB using the Program Link."""
    contact_entry = collection_contacts.find_one({"Program Link": program_link}, {"Contacts": 1})
    return contact_entry.get("Contacts", []) if contact_entry else []

def get_application_deadlines(program_link):
    """Fetch application deadlines from MongoDB using the Program Link."""
    deadlines_entry = collection_contacts.find_one({"Program Link": program_link}, {"Application Deadlines": 1})
    return deadlines_entry.get("Application Deadlines", {}) if deadlines_entry else []

def recommend_universities(resume_text):
    """Finds the best university programs based on the structured resume data."""
    query_embedding = get_embedding(resume_text)

    if query_embedding is None:
        return []

    query_embedding = np.expand_dims(query_embedding, axis=0)

    # Search FAISS index for nearest neighbors
    k = random.randint(7, 17)
    with st.spinner("🔍 Finding best university matches..."):
        distances, indices = index.search(query_embedding, k)
        time.sleep(1)

    # Get recommended universities and fetch their contact details & deadlines
    recommendations = []
    for i in range(k):
        if indices[0][i] >= 0 and indices[0][i] < len(university_metadata):
            row = university_metadata.iloc[indices[0][i]]
            program_link = row["Program Link"]

            # Fetch contact details
            contacts = get_contact_details(program_link)
            university_portal_link = get_university_portal_link(program_link)

            # Fetch application deadlines
            deadlines = get_application_deadlines(program_link)

            recommendations.append({
                "University": row["University Name"],
                "Program": row["Program Title"],
                "Program Link": program_link,
                "University Portal Link": university_portal_link,
                "Distance Score": distances[0][i],
                "Contacts": contacts,
                "Deadlines": deadlines
            })

    return recommendations

def main():
    st.warning("⚠️ **Disclaimer:** This tool is still in development and some of the features will be improved in the future. The recommendations provided are based on a dataset of German universities and programs.")
    st.title("🎓 Universität Kompass")
    st.write("*AI-powered German university program recommendations based on your resume.*")
    st.write("**Upload your resume, and we'll find the best matching university programs for you!**")

    uploaded_file = st.file_uploader("📂 Upload your resume (PDF format)", type="pdf")

    if uploaded_file is not None:
        st.info("✅ Resume uploaded successfully!")

        # Progress indicator
        progress = st.progress(0)

        # Step 1: Extract raw text
        progress.progress(10)
        raw_resume_text = extract_resume_text(uploaded_file)

        # Step 2: Extract structured sections using OpenAI
        progress.progress(40)
        structured_resume_text = extract_relevant_info(raw_resume_text)
        name, email = extract_name_email(structured_resume_text)
        if structured_resume_text is None:
            st.stop()
        else:

            # Step 3: Find university matches
            if st.button("🔍 Find Best University Programs"):
                with st.spinner("🔎 Searching for best matches..."):
                    progress.progress(70)
                    recommendations = recommend_universities(structured_resume_text)
                    progress.progress(100)
                    time.sleep(1)
    
                # Display results
                if recommendations:
                    st.subheader("🎯 Recommended University Programs:")
                    
                    for i, rec in enumerate(recommendations, 1):
                        # Create a container for each university
                        with st.container():
                            # Always visible information
                            st.markdown(f"### {i}. 🏫 {rec['University']}")
                            st.markdown(f"🎓 *{rec['Program']}*")
                            
                            # Create an expander for additional details
                            with st.expander("View Details"):
                                # Create tabs for different sections
                                tabs = st.tabs(["Deadlines", "Program Info", "Contacts"])
                                
                                # Deadlines Tab
                                with tabs[0]:
                                    if rec['Deadlines']:
                                        display_deadlines(rec['Deadlines'])
                                    else:
                                        st.info("No deadline information available")
                                        
                                # Program Info Tab
                                with tabs[1]:
                                    st.markdown(f"**University Portal Link:** [Click here to visit]({rec['University Portal Link']})")
                                    #st.markdown(f"**Match Score:** {(1 - rec['Distance Score']) * 100:.2f}%")
                                
                                # Contacts Tab
                                with tabs[2]:
                                    if rec['Contacts']:
                                        for contact in rec['Contacts']:
                                            st.markdown(f"### 📌 {contact.get('Contact Type', 'General Contact')}")
                                            display_contact(contact)
                                            st.markdown("---")
                                    else:
                                        st.info("No contact information available")
                                
                            
                            st.markdown("---")
                else:
                    st.warning("⚠️ No recommendations found. Try a different resume.")
    
if __name__ == "__main__":
    main()
    