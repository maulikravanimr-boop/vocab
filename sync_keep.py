import os
import re
import sys
import json
import urllib.request
import urllib.error

try:
    import gkeepapi
except ImportError:
    gkeepapi = None

GUJARATI_NOTE_ID = "1v6H1GvnifFATLmT9RFby3R2iD2FW_-MR75_fdd2DyX0TJnwvrw4ZZ9IWqm93ReqAPCBA"
URDU_NOTE_ID = "1IpD0T8F3MnrigfxVUsjAjSaSRwaI1S2CbtSOxfGAXYYsJmolp57a7xJ6AnRs45ZlasPV"

def parse_note_lines(text, default_lang="Hindi & Urdu"):
    entries = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines:
        if ":" in line:
            term, meaning = line.split(":", 1)
            term = term.strip()
            meaning = meaning.strip()
        else:
            term = line.strip()
            meaning = "Added from Keep notes"
            
        if not term:
            continue
            
        entries.append({
            "term": term,
            "meaning": meaning,
            "lang": default_lang
        })
    return entries

def build_enrichment_prompt(terms_list, lang):
    return f"""You are an expert linguist specializing in {lang}, Hindi, Urdu, and Gujarati vocabulary.
For each of the following words/phrases, generate a rich vocabulary flashcard entry in valid JSON.
Words to enrich:
{json.dumps(terms_list, ensure_ascii=False)}

Return a JSON array where each object has these exact keys:
- "word": Romanized word title (string)
- "script": Native script (Devanagari/Nastaliq for Hindi/Urdu, Gujarati script for Gujarati) (string)
- "meaning": Concise, clear English definition (string)
- "notes": Etymology, cultural usage, or nuance (string)
- "example_orig": Authentic example sentence in native script (string)
- "example_translit": Romanized transliteration of the example sentence (string)
- "example_en": English translation of the example sentence (string)
- "distractors": An array of exactly 3 plausible, believable multiple-choice distractors of the same semantic register in English (list of strings). STRICT REQUIREMENT: If the word is Gujarati, all distractors must be plausible Gujarati definitions. If Hindi/Urdu, all distractors must be plausible Hindi/Urdu definitions.

Output ONLY the JSON array, with no markdown fences or additional commentary.
"""

def enrich_words_with_gemini(terms_list, lang, api_key):
    if not api_key:
        print(f"Notice: GEMINI_API_KEY not configured. Creating base entries without AI sentences for {lang}.")
        results = []
        for item in terms_list:
            results.append({
                "word": item["term"],
                "script": item["term"],
                "meaning": item["meaning"],
                "notes": "Added from Keep notes",
                "example_orig": item["term"],
                "example_translit": "",
                "example_en": item["meaning"],
                "distractors": [
                    "Alternative meaning 1",
                    "Alternative meaning 2",
                    "Alternative meaning 3"
                ]
            })
        return results

    print(f"Calling Gemini API to generate scripts, authentic example sentences, and believable distractors for {len(terms_list)} {lang} words...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    prompt = build_enrichment_prompt(terms_list, lang)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text_content = data["candidates"][0]["content"]["parts"][0]["text"]
            enriched = json.loads(text_content)
            print(f"Successfully generated AI sentences and options for {len(enriched)} words.")
            return enriched
    except Exception as e:
        print(f"Gemini API request failed: {e}. Using fallback format.")
        results = []
        for item in terms_list:
            results.append({
                "word": item["term"],
                "script": item["term"],
                "meaning": item["meaning"],
                "notes": "Added from Keep notes",
                "example_orig": item["term"],
                "example_translit": "",
                "example_en": item["meaning"],
                "distractors": [
                    "Alternative meaning 1",
                    "Alternative meaning 2",
                    "Alternative meaning 3"
                ]
            })
        return results

def sync_keep_to_html():
    google_email = os.environ.get("GOOGLE_EMAIL")
    master_token = os.environ.get("GOOGLE_MASTER_TOKEN")
    app_password = os.environ.get("GOOGLE_APP_PASSWORD")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    if not google_email:
        print("Error: Missing GOOGLE_EMAIL environment variable.")
        sys.exit(1)

    if not master_token and not app_password:
        print("Error: Missing GOOGLE_MASTER_TOKEN or GOOGLE_APP_PASSWORD.")
        sys.exit(1)

    if not gkeepapi:
        print("Error: gkeepapi library is not installed. Run: pip install gkeepapi")
        sys.exit(1)

    keep = gkeepapi.Keep()
    
    print(f"Authenticating with Google Keep as {google_email}...")
    authenticated = False
    if master_token:
        try:
            keep.authenticate(google_email, master_token)
            authenticated = True
            print("Successfully authenticated using master token.")
        except Exception as e:
            print(f"Master token authentication failed: {e}")

    if not authenticated and app_password:
        try:
            keep.login(google_email, app_password)
            authenticated = True
            print("Successfully logged in using app password.")
        except Exception as e:
            print(f"App password login failed: {e}")

    if not authenticated:
        print("Authentication failed. Please verify credentials in GitHub Secrets.")
        sys.exit(1)

    print("Fetching Keep notes...")
    note_guj = keep.get(GUJARATI_NOTE_ID)
    if not note_guj:
        note_guj = keep.find(query="Gujarati wordbank")
        note_guj = list(note_guj)[0] if note_guj else None

    note_urdu = keep.get(URDU_NOTE_ID)
    if not note_urdu:
        note_urdu = keep.find(query="Urdu/Hindi wordbank")
        note_urdu = list(note_urdu)[0] if note_urdu else None

    guj_entries = parse_note_lines(note_guj.text, "Gujarati") if note_guj else []
    urdu_entries = parse_note_lines(note_urdu.text, "Hindi & Urdu") if note_urdu else []

    print(f"Retrieved {len(guj_entries)} Gujarati entries and {len(urdu_entries)} Hindi/Urdu entries from Keep.")

    # Read current index.html
    html_path = "index.html"
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        sys.exit(1)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    m = re.search(r"const DEFAULT_WORDS = (\[.*?\]);", html, re.DOTALL)
    existing_words = json.loads(m.group(1)) if m else []
    existing_by_term = {w["word"].lower().strip(): w for w in existing_words}

    # Find new terms not yet in existing_words
    new_guj = [item for item in guj_entries if item["term"].lower().strip() not in existing_by_term]
    new_urdu = [item for item in urdu_entries if item["term"].lower().strip() not in existing_by_term]

    if not new_guj and not new_urdu:
        print("No new vocabulary found in Keep notes. Everything is up to date!")
        return

    print(f"Found {len(new_guj)} new Gujarati words and {len(new_urdu)} new Hindi/Urdu words to enrich.")

    enriched_guj = enrich_words_with_gemini(new_guj, "Gujarati", gemini_api_key) if new_guj else []
    enriched_urdu = enrich_words_with_gemini(new_urdu, "Hindi & Urdu", gemini_api_key) if new_urdu else []

    merged_words = list(existing_words)

    for item in enriched_guj:
        merged_words.append({
            "id": f"gu-auto-{len(merged_words) + 1}",
            "word": item.get("word", ""),
            "script": item.get("script", ""),
            "lang": "Gujarati",
            "category": "Gujarati",
            "meaning": item.get("meaning", ""),
            "notes": item.get("notes", "Added from Keep notes"),
            "example_orig": item.get("example_orig", ""),
            "example_translit": item.get("example_translit", ""),
            "example_en": item.get("example_en", ""),
            "distractors": item.get("distractors", [])
        })

    for item in enriched_urdu:
        merged_words.append({
            "id": f"hi-auto-{len(merged_words) + 1}",
            "word": item.get("word", ""),
            "script": item.get("script", ""),
            "lang": "Urdu / Hindi",
            "category": "Hindi & Urdu",
            "meaning": item.get("meaning", ""),
            "notes": item.get("notes", "Added from Keep notes"),
            "example_orig": item.get("example_orig", ""),
            "example_translit": item.get("example_translit", ""),
            "example_en": item.get("example_en", ""),
            "distractors": item.get("distractors", [])
        })

    print(f"Total vocabulary after enrichment: {len(merged_words)} words.")

    json_str = json.dumps(merged_words, ensure_ascii=False)
    new_html = re.sub(
        r"const DEFAULT_WORDS = \[.*?\];",
        f"const DEFAULT_WORDS = {json_str};",
        html,
        flags=re.DOTALL
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_html)

    print("index.html successfully updated with AI-enriched vocabulary!")

if __name__ == "__main__":
    sync_keep_to_html()
