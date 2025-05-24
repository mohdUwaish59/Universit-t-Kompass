import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
import logging
from dotenv import load_dotenv
from time import sleep
from random import randint

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Source DB (where program links are stored)
source_db = client["Kompass_daad_university_data_master_en"]
source_collection = source_db["programs"]

# Target DB (where we store scraped details)
target_db = client["University_Programs"]
target_collection = target_db["Programs_Details"]

# Logging configuration
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


def extract_section(soup, title):
    """Extracts content from a section given the title."""
    try:
        section = soup.find('h5', text=title)
        if section:
            parent_div = section.find_parent('div')
            if parent_div:
                if parent_div.find('ul'):
                    return [li.text.strip() for li in parent_div.find_all('li')]
                elif parent_div.find('p'):
                    return parent_div.find('p').text.strip()
        return []
    except Exception as e:
        logging.warning(f"Error extracting section '{title}': {e}")
        return []


def extract_contacts(soup):
    """Extracts multiple contacts from the page under 'qa-contact-list'."""
    contacts = []
    contact_sections = soup.find_all('div', class_="qa-contact-list")

    print(f"Found {len(contact_sections)} contact sections.")

    for section in contact_sections:
        contact_type = section.find('h4').text.strip() if section.find('h4') else "Unknown"
        contact_items = section.find_all('div', class_="qa-contact")

        for item in contact_items:
            contact_data = {"Contact Type": contact_type}
            headline = item.find('h5')
            contact_data["Name"] = headline.text.strip() if headline else None

            address = item.find('dd', class_="qa-address")
            contact_data["Address"] = address.text.strip() if address else None

            postal_code = item.find('dd', class_="qa-zip")
            contact_data["Postal Code"] = postal_code.text.strip() if postal_code else None

            city = item.find('dd', class_="qa-city")
            contact_data["City"] = city.text.strip() if city else None

            phone = item.find('a', class_="qa-phone")
            contact_data["Phone"] = phone.text.strip() if phone else None

            fax = item.find('a', class_="qa-fax")
            contact_data["Fax"] = fax.text.strip() if fax else None

            email = item.find('a', class_="qa-email")
            contact_data["Email"] = email.text.strip() if email else None

            website = item.find('a', class_="qa-web")
            contact_data["Website"] = website['href'] if website else None

            print(f"Extracted contact: {contact_data}")
            contacts.append(contact_data)

    return contacts


def scrape_program_details():
    """Fetches and updates detailed program data from stored links in MongoDB."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Fetch program links from the existing database
    programs = list(source_collection.find({}, {"Program Link": 1}))

    print(f"Total programs found in source DB: {len(programs)}")

    if not programs:
        print("⚠️ No program links found in source DB. Exiting script.")
        return

    for program in programs:
        program_url = program.get("Program Link")
        if not program_url or program_url == "Not found":
            print(f"⚠️ Skipping invalid URL: {program_url}")
            continue

        print(f"Fetching: {program_url}")

        try:
            response = requests.get(program_url, headers=headers, timeout=10)
            print(f"Status for {program_url}: {response.status_code}")
            if response.status_code != 200:
                logging.warning(f"⚠️ Failed to retrieve details for {program_url}: Status {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            area_of_study = extract_section(soup, "Area of study")
            focus = extract_section(soup, "Focus")
            target_group = extract_section(soup, "Target group")
            contacts = extract_contacts(soup)

            update_data = {
                "Program Link": program_url,
                "Area of Study": area_of_study if area_of_study else None,
                "Focus": focus if focus else None,
                "Target Group": target_group if target_group else None,
                "Contacts": contacts if contacts else []
            }

            print(f"Extracted Data for {program_url}: {update_data}")

            target_collection.update_one(
                {"Program Link": program_url},
                {"$set": update_data},
                upsert=True
            )
            print(f"✅ Updated database for: {program_url}\n")

        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Request failed for {program_url}: {e}")

        sleep(randint(2, 5))  # Random delay to prevent overloading the server


# Execute phase 2 scraping
if __name__ == "__main__":
    scrape_program_details()
