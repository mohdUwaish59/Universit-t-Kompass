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

def extract_university_details(soup):
    """
    Extracts the university profile image and course detail link from the given HTML soup.
    """
    university_data = {}

    # Extract university profile image
    profile_image = soup.find('picture', class_="qa-picture")
    if profile_image:
        img_tag = profile_image.find('img')
        if img_tag and img_tag.get('src'):
            university_data['Profile Image'] = img_tag['src']

    # Extract university website link
    course_detail_link = soup.find('a', class_="sidebar-image__link")
    if course_detail_link and course_detail_link.get('href'):
        university_data['Course Detail Link'] = course_detail_link['href']

    return university_data

def scrape_university_links():
    """
    Fetches each program link from the database, scrapes the university details,
    and updates the database.
    """
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

            # Extract university details
            university_details = extract_university_details(soup)

            if university_details:
                # Update MongoDB with university details
                collection.update_one(
                    {"Program Link": program_url},
                    {"$set": university_details}
                )
                print(f"✅ Updated university details for: {program_url}")
            else:
                print(f"⚠️ No university details found for: {program_url}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for {program_url}: {e}")

        time.sleep(2)  # Prevent overwhelming the server

# Execute the scraping function
if __name__ == "__main__":
    scrape_university_links()
