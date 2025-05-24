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

def get_total_pages(base_url):
    """Fetches the total number of pages from the select dropdown"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        print("Failed to retrieve the total page count.")
        return 1
    
    soup = BeautifulSoup(response.text, 'html.parser')
    page_select = soup.find('select')
    
    if not page_select:
        print("Failed to find the page selector.")
        return 1
    
    options = page_select.find_all('option')
    total_pages = max([int(option.text) for option in options if option.text.isdigit()])
    print(f"Total pages found: {total_pages}")
    return total_pages

def scrape_programs(base_url):
    """Fetches and parses the DAAD website content to extract all program details from all pages and save to MongoDB"""
    total_pages = get_total_pages(base_url)
    all_programs = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    for page in range(1, total_pages + 1):
        page_url = f"{base_url}&hec-p={page}" if page > 1 else base_url
        response = requests.get(page_url, headers=headers)
        
        if response.status_code != 200:
            print(f"Failed to retrieve page {page}")
            continue
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Finding all program containers
        program_list = soup.find_all('li', class_='qa-db-result-item')
        
        for program in program_list:
            university_info = program.find('span', class_='js-dynamic-content u-display-block u-font-regular u-size-18 result__headline-content mb-8')
            program_title_info = program.find('span', class_='js-dynamic-content u-display-block u-font-light u-size-24 result__headline-content mb-24 u-size-32@lg')
            link_tag = program.find('a', class_='link link--nowrap u-stretched-link u-position-static result__link qa-more-link u-text-primary u-font-italic')
            
            university_name = university_info.text.strip() if university_info else "Not found"
            program_name = program_title_info.text.strip() if program_title_info else "Not found"
            program_url = "https://www.daad.de" + link_tag['href'] if link_tag and link_tag.get('href') else "Not found"
            
            program_data = {
                "University Name": university_name,
                "Program Title": program_name,
                "Program Link": program_url
            }
            
            # Store results in MongoDB
            collection.insert_one(program_data)
            
            # Store in list as well
            all_programs.append(program_data)
            
            # Displaying results
            print("University Name:", university_name)
            print("Program Title:", program_name)
            print("Program Link:", program_url)
            print("-" * 50)  # Separator for clarity
    
    return all_programs

# Example usage
base_url = "https://www.daad.de/en/studying-in-germany/universities/all-degree-programmes/?hec-degreeType=37&hec-teachingLanguage=2"
scrape_programs(base_url)
