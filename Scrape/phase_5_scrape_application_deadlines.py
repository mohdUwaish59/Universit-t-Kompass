import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Database and collection
db = client["Kompass_daad_university_data_master_en"]
collection = db["programs"]

def extract_deadlines(soup):
    """Extracts all application deadlines from the page."""
    deadlines_data = {}

    deadline_sections = soup.find_all('div', class_="deadlines")
    
    for section in deadline_sections:
        semester_header = section.find('h5')
        if semester_header:
            semester = semester_header.text.strip()
            deadlines = []

            for item in section.find_all('li'):
                deadline_type = item.find('h6').text.strip() if item.find('h6') else "Unknown Deadline"
                deadline_dates = item.find('p').text.strip() if item.find('p') else "Dates not found"

                deadlines.append({
                    "Type": deadline_type,
                    "Dates": deadline_dates
                })

            deadlines_data[semester] = deadlines

    return deadlines_data

def scrape_application_deadlines():
    """Fetches and updates application deadlines for each program link in MongoDB."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    programs = collection.find({}, {"Program Link": 1})

    for program in programs:
        program_url = program.get("Program Link")
        if not program_url or program_url == "Not found":
            print(f"⚠️ Skipping invalid URL: {program_url}")
            continue

        print(f"Fetching: {program_url}")

        try:
            response = requests.get(program_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to retrieve {program_url}: Status {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract deadlines
            deadlines = extract_deadlines(soup)

            if deadlines:
                # Update MongoDB with deadlines
                collection.update_one(
                    {"Program Link": program_url},
                    {"$set": {"Application Deadlines": deadlines}}
                )
                print(f"✅ Updated deadlines for: {program_url}")
            else:
                print(f"⚠️ No deadlines found for: {program_url}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for {program_url}: {e}")

        time.sleep(2)  # Prevent overwhelming the server

# Execute the scraping function
if __name__ == "__main__":
    scrape_application_deadlines()
