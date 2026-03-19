import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
import time
from tqdm import tqdm

BASE_URL = "https://www.carakasamhitaonline.com"
START_PAGE = "https://www.carakasamhitaonline.com/index.php?title=Adhyaya(chapters)"

# Upgraded headers to perfectly mimic a real desktop browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive"
}

SAVE_DIR = "charaka_structured_data"
os.makedirs(SAVE_DIR, exist_ok=True)

# ---------------------------------------------------------
# SET UP ROBUST HTTP SESSION
# ---------------------------------------------------------
session = requests.Session()
# This will automatically retry up to 5 times if the server drops the connection
retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))
session.mount('http://', HTTPAdapter(max_retries=retries))


def is_sanskrit(text):
    return bool(re.search(r"[\u0900-\u097F]", text))


def is_transliteration(text):
    if not is_sanskrit(text) and re.search(r"\|\|\s*\d+\s*\|\|", text):
        return True
    return False


def extract_chapter_links():
    # Added timeout=15 so it fails gracefully instead of hanging forever
    res = session.get(START_PAGE, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(res.text, "lxml")
    links = []
    
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "Adhyaya" in href and "title=" in href and "&action=" not in href:
            full_url = urljoin(BASE_URL, href)
            links.append(full_url)
            
    return list(set(links))


def scrape_structured_chapter(url):
    res = session.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(res.text, "lxml")
    
    heading = soup.find("h1")
    chapter_title = heading.get_text(strip=True) if heading else "Unknown_Chapter"
    chapter_title = re.sub(r'[\\/*?:"<>|]', "", chapter_title).strip()
    
    content_div = soup.find("div", {"id": "mw-content-text"})
    if not content_div:
        return []

    raw_text = content_div.get_text(separator="\n\n", strip=True)
    blocks = raw_text.split("\n\n")

    paired_data = []
    current_sanskrit = []
    current_english = []
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        if is_sanskrit(block):
            if current_sanskrit and current_english:
                paired_data.append({
                    "chapter": chapter_title,
                    "sanskrit": " ".join(current_sanskrit),
                    "english": " ".join(current_english)
                })
                current_sanskrit = []
                current_english = []
            
            current_sanskrit.append(block)
            
        elif is_transliteration(block):
            continue
            
        else:
            if current_sanskrit:
                clean_block = re.sub(r"\[.*?\]", "", block).strip()
                if clean_block:
                    current_english.append(clean_block)
                    
    if current_sanskrit and current_english:
        paired_data.append({
            "chapter": chapter_title,
            "sanskrit": " ".join(current_sanskrit),
            "english": " ".join(current_english)
        })

    return paired_data


def main():
    print("Fetching chapter links...")
    try:
        links = extract_chapter_links()
        print(f"Found {len(links)} chapters. Starting structured extraction...")
    except requests.exceptions.RequestException as e:
        print(f"CRITICAL ERROR: Could not connect to the website. \nDetails: {e}")
        print("Please check if the website is currently down in your browser.")
        return
    
    all_structured_data = []
    
    for link in tqdm(links):
        try:
            chapter_pairs = scrape_structured_chapter(link)
            all_structured_data.extend(chapter_pairs)
            time.sleep(2) # Increased delay to 2 seconds to be extra polite to their server
        except Exception as e:
            print(f"Error scraping {link}: {e}")
            
    output_file = os.path.join(SAVE_DIR, "raw_charaka.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_structured_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nScraping Complete! Extracted {len(all_structured_data)} locked pairs.")
    print(f"Data saved to {output_file}")


if __name__ == "__main__":
    main()