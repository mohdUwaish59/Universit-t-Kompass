from pymongo import MongoClient
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Source DB (contains contacts)
source_db = client["University_Programs"]
source_collection = source_db["Programs_Details"]

# Target DB (to update with contacts)
target_db = client["Kompass_daad_university_data_master_en"]
target_collection = target_db["programs"]

# Logging configuration
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


def transfer_contacts():
    """Fetch contacts from University_Programs and update Kompass_daad_university_data_master_en."""
    
    # Fetch all program links with contacts from the source DB
    programs_with_contacts = list(source_collection.find({}, {"Program Link": 1, "Contacts": 1}))

    print(f"Total programs with contacts found: {len(programs_with_contacts)}")

    if not programs_with_contacts:
        print("⚠️ No programs with contacts found in source DB. Exiting script.")
        return

    updated_count = 0

    for program in programs_with_contacts:
        program_link = program.get("Program Link")
        contacts = program.get("Contacts", [])

        if not program_link:
            print("⚠️ Skipping entry with missing Program Link.")
            continue

        if not contacts:
            print(f"⚠️ No contacts found for {program_link}. Skipping update.")
            continue

        # Update the target collection where "Program Link" matches
        result = target_collection.update_one(
            {"Program Link": program_link},
            {"$set": {"Contacts": contacts}}
        )

        if result.matched_count > 0:
            updated_count += 1
            print(f"✅ Updated contacts for: {program_link}")
        else:
            print(f"⚠️ No matching program found for: {program_link}")

    print(f"\n🎯 Transfer complete! Total updated programs: {updated_count}")


# Execute the transfer process
if __name__ == "__main__":
    transfer_contacts()
