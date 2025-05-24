import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB Atlas connection
client = MongoClient(MONGO_URI)
db = client.get_database("Kompass_daad_university_data_master_en")
collection = db.get_collection("programs")

def extract_section(soup, title):
    """Extracts content from a section given the title"""
    section = soup.find('h5', text=title)
    if section:
        parent_div = section.find_parent('div')
        if parent_div:
            if parent_div.find('ul'):
                return [li.text.strip() for li in parent_div.find_all('li')]
            else:
                return parent_div.find('p').text.strip() if parent_div.find('p') else None
    return None

def scrape_program_details():
    """Fetches and updates detailed program data from stored links in MongoDB"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    programs = collection.find({}, {"Program Link": 1})
    
    for program in programs:
        program_url = program.get("Program Link")
        if not program_url or program_url == "Not found":
            continue
        
        response = requests.get(program_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to retrieve details for {program_url}")
            continue
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        area_of_study = extract_section(soup, "Area of study")
        focus = extract_section(soup, "Focus")
        target_group = extract_section(soup, "Target group")
        
        update_data = {}
        if area_of_study:
            update_data["Area of Study"] = area_of_study
        if focus:
            update_data["Focus"] = focus
        if target_group:
            update_data["Target Group"] = target_group
        
        if update_data:
            collection.update_one({"Program Link": program_url}, {"$set": update_data})
            print(f"Updated program: {program_url}")

# Execute phase 2 scraping
scrape_program_details()
