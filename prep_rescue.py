import os
import re
import json
from tqdm import tqdm

INPUT_DIR = "charaka_data/chapters"
OUTPUT_DIR = "charaka_preprocessed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# We will chunk long English explanations into 100-word blocks
CHUNK_WORD_LIMIT = 100

def chunk_english_text(english_list, limit=CHUNK_WORD_LIMIT):
    """Takes a list of English sentences and chunks them by word count."""
    full_text = " ".join(english_list)
    words = full_text.split()
    chunks = []
    
    for i in range(0, len(words), limit):
        chunk = " ".join(words[i:i+limit])
        if len(chunk) > 30: # Ignore tiny leftover fragments
            chunks.append(chunk)
            
    return chunks

def process_chapter(chapter_name, text):
    lines = text.split("\n")
    
    paired_chunks = []
    current_shloka = []
    current_english = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 1. Look for Devanagari (Sanskrit)
        if re.search(r"[\u0900-\u097F]", line):
            # If we hit a new Shloka and already have English saved, package the previous pair!
            if current_shloka and current_english:
                english_chunks = chunk_english_text(current_english)
                shloka_text = " ".join(current_shloka)
                
                # Clone the Shloka for every English chunk
                for eng_chunk in english_chunks:
                    paired_chunks.append({
                        "chapter": chapter_name,
                        "sanskrit": shloka_text,
                        "english": eng_chunk
                    })
                    
                # Reset for the new verse
                current_shloka = []
                current_english = []
                
            current_shloka.append(line)
            
        # 2. Look for English/Numbers
        elif re.search(r"[a-zA-Z]", line):
            # Skip transliteration (usually contains || numbers || or random short English strings mixed with numbers)
            if re.search(r"\|\|\s*\d+\s*\|\|", line):
                continue
                
            # If we have an active Shloka, this must be its translation/explanation
            if current_shloka:
                # Clean up bracket citations like [1]
                clean_line = re.sub(r"\[.*?\]", "", line).strip()
                if clean_line:
                    current_english.append(clean_line)
                    
    # Catch the very last verse in the chapter
    if current_shloka and current_english:
        english_chunks = chunk_english_text(current_english)
        shloka_text = " ".join(current_shloka)
        for eng_chunk in english_chunks:
            paired_chunks.append({
                "chapter": chapter_name,
                "sanskrit": shloka_text,
                "english": eng_chunk
            })
            
    return paired_chunks

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Error: Could not find the directory '{INPUT_DIR}'.")
        return

    chapters = os.listdir(INPUT_DIR)
    print(f"Found {len(chapters)} chapters in local data. Starting rescue parse...")
    
    all_paired_chunks = []
    
    for chapter in tqdm(chapters):
        text_path = os.path.join(INPUT_DIR, chapter, "text.txt")
        if not os.path.exists(text_path):
            continue
            
        with open(text_path, "r", encoding="utf8") as f:
            text = f.read()
            
        chapter_chunks = process_chapter(chapter, text)
        all_paired_chunks.append(chapter_chunks)
        
    # Flatten the list of lists
    flat_chunks = [chunk for chapter in all_paired_chunks for chunk in chapter]
    
    # Remove exact duplicates just in case
    unique_chunks = []
    seen = set()
    for c in flat_chunks:
        identifier = c["sanskrit"] + c["english"]
        if identifier not in seen:
            seen.add(identifier)
            unique_chunks.append(c)
            
    output_file = os.path.join(OUTPUT_DIR, "charaka_paired_chunks.json")
    with open(output_file, "w", encoding="utf8") as f:
        json.dump(unique_chunks, f, indent=2, ensure_ascii=False)
        
    print("\nRescue Preprocessing Complete!")
    print(f"Total Paired Chunks Created: {len(unique_chunks)}")
    print(f"Saved to: {output_file}")

if __name__ == "__main__":
    main()