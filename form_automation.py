import re
import time
import os
import requests
from playwright.sync_api import sync_playwright

# --- Configuration ---
PDF_LIST_FILE = "pdfs.txt"
HISTORY_FILE = "upload_history.txt"

FORM_URL = "https://curtiscenter.math.ucla.edu/ammp-unofficial-transcript/"
USER_DETAILS = {
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com"
}
# ---------------------

def load_processed_files():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def mark_as_processed(identifier):
    with open(HISTORY_FILE, 'a') as f:
        f.write(f"{identifier}\n")

def get_pdf_sources():
    if not os.path.exists(PDF_LIST_FILE):
        print(f"Error: {PDF_LIST_FILE} not found. Please create it and add PDF URLs/filenames.")
        return []
    with open(PDF_LIST_FILE, 'r') as f:
        # Filter out comments and empty lines
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def download_file(url_or_path):
    """Downloads file if it's a URL, otherwise returns the local path."""
    if url_or_path.startswith("http"):
        filename = url_or_path.split('/')[-1]
        print(f"Downloading {filename} from {url_or_path}...")
        response = requests.get(url_or_path)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return os.path.abspath(filename)
        else:
            print(f"Failed to download {url_or_path}")
            return None
    else:
        # Assume it's a local file
        if os.path.exists(url_or_path):
            return os.path.abspath(url_or_path)
        else:
            print(f"File not found: {url_or_path}")
            return None

def solve_math_captcha(page):
    try:
        # Get the label text for the math challenge
        label_selector = 'label[id^="nf-label-field-2851"]'
        question_text = page.inner_text(label_selector)
        print(f"Math question found: {question_text}")
        
        # Extract numbers (e.g. "5 + 7 = ?") or "Five + Seven"
        match = re.search(r'(\d+)\s*\+\s*(\d+)', question_text)
        if match:
            num1 = int(match.group(1))
            num2 = int(match.group(2))
            answer = num1 + num2
            print(f"Calculated answer: {answer}")
            return str(answer)
    except Exception as e:
        print(f"Error solving math captcha: {e}")
    return None

def fill_and_submit(page, file_path):
    print(f"Navigate and Fill form for: {file_path}")
    page.goto(FORM_URL)
    
    # Wait for form to load
    page.wait_for_selector('#nf-field-1660')
    
    # Fill Basic Fields
    page.fill('#nf-field-1660', USER_DETAILS["first_name"])
    page.fill('#nf-field-1661', USER_DETAILS["last_name"])
    page.fill('#nf-field-1662', USER_DETAILS["email"])
    
    # Upload PDF
    print(f"Uploading {os.path.basename(file_path)}...")
    page.set_input_files('#nf-field-1666', file_path)
    
    # Solve Math Captcha
    answer = solve_math_captcha(page)
    if answer:
        page.fill('#nf-field-2851', answer)
        time.sleep(1) # Small pause for UI update
        
        # Click Submit
        page.click('#nf-field-1667')
        print("Submitted form.")
        
        # Wait for confirmation or completion
        try:
            success_element = page.wait_for_selector('.nf-response-msg', timeout=15000)
            success_text = success_element.inner_text()
            print(f"Submission successful! Response: {success_text}")
            return success_text
        except:
            print("Warning: Confirmation message timeout. Moving to next...")
            # Decide if timeout counts as success or not. Usually safer to say False if unsure.
            # But if it submitted, we might want to verify manually. 
            # For now, let's assume if no error on submit click, it might be ok, but timeout is bad.
            return False
    else:
        print("Skipping submission due to captcha failure.")
        return False

import sys
import argparse

def run_single_file(file_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Ensure absolute path
        abs_path = os.path.abspath(file_path)
        
        try:
            fill_and_submit(page, abs_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Automate form submission for a PDF.')
    parser.add_argument('file_path', help='Path to the PDF file to upload')
    args = parser.parse_args()
    
    run_single_file(args.file_path)
