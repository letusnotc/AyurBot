import os
import json as json_lib
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer, CrossEncoder
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from ddgs import DDGS
    DDG_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS  # fallback for older installs
        DDG_AVAILABLE = True
    except ImportError:
        DDG_AVAILABLE = False
        print("[WARNING] ddgs not installed. Run: pip install ddgs")

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
    llm = genai.GenerativeModel('gemini-2.5-flash')
else:
    llm = None
    print("\n[WARNING] No API key provided in .env. Ayurbot will skip LLM generation.")

print("Loading embedding model...")
embed_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

print("Loading reranker...")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

print("Connecting to paired Vector DB...")
DB_DIR = "./charaka_paired_db"
client = chromadb.Client(Settings(persist_directory=DB_DIR, is_persistent=True))
collection = client.get_collection("charaka_samhita_paired")

app = Flask(__name__)
CORS(app)

# ==========================================
# LANGUAGE SUPPORT
# ==========================================
SUPPORTED_LANGUAGES = {
    "English": "English",
    "Hindi": "Hindi (हिंदी)",
    "Chhattisgarhi": "Chhattisgarhi (छत्तीसगढ़ी)",
    "Marathi": "Marathi (मराठी)",
    "Bengali": "Bengali (বাংলা)",
    "Tamil": "Tamil (தமிழ்)"
}


def translate_to_english(text):
    """Translate query to English for RAG retrieval using Gemini."""
    if not llm:
        return text
    try:
        resp = llm.generate_content(
            f"Translate the following text to English. Return ONLY the translation, no explanations:\n\n{text}"
        )
        return resp.text.strip()
    except Exception:
        return text


def parse_llm_json(text):
    """Robustly extract and parse a JSON object from LLM response text."""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            if part.startswith("json"):
                text = part[4:].strip()
                break
            elif "{" in part:
                text = part.strip()
                break
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json_lib.loads(text)


# ==========================================
# CHAT — RAG PIPELINE
# ==========================================
def get_refined_answer(query, combined_context, language="English"):
    if not llm:
        return "Please add your API key to .env to generate refined answers."

    if combined_context.strip():
        context_section = f"### CONTEXT FROM DATABASE:\n{combined_context}"
    else:
        context_section = "### NOTE: No direct context was found in the database. Use your internal knowledge of Charaka Samhita to answer, provided the query is Ayurvedic."

    lang_name = SUPPORTED_LANGUAGES.get(language, "English")
    lang_instruction = ""
    if language and language != "English":
        lang_instruction = (
            f"\n7. CRITICAL: Your ENTIRE response must be written in {lang_name}. "
            f"Every heading, bullet point, explanation, and translation must be in {lang_name}. "
            f"Only the Devanagari Sanskrit Shloka verse itself should remain unchanged."
        )

    prompt = f"""
    You are Ayurbot, an expert Ayurvedic AI assistant with deep knowledge of the Charaka Samhita.
    A user has asked: "{query}"

    {context_section}

    STRICT GUIDELINES:
    1. If the query is related to Ayurveda (medicine, herbs, philosophy, lifestyle, etc.), provide a thorough and refined answer.
    2. If the query is NOT related to Ayurveda, politely state that you can only assist with Ayurvedic knowledge.
    3. If database context is provided, prioritize it. If not, use your internal knowledge of ancient scriptures.
    4. MANDATORY: At the very end of your response, provide the single most relevant Sanskrit Shloka (IN DEVANAGARI SCRIPT) from the Charaka Samhita that describes or justifies the answer. Include its translation and label it as: "### 📜 Relevant Shloka".
    5. Use markdown (bold, bullets) to make your response structured and beautiful.
    6. Keep your answer thorough but concise.{lang_instruction}
    """

    try:
        response = llm.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating refined answer: {e}"


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    query = data.get("query")
    top_k = data.get("top_k", 5)
    language = data.get("language", "English")

    if not query:
        return jsonify({"error": "No query provided"}), 400

    # Translate non-English query to English for vector retrieval
    retrieval_query = query
    if language != "English":
        retrieval_query = translate_to_english(query)

    query_embedding = embed_model.encode([retrieval_query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=15)

    docs = results["documents"][0]
    metas = results["metadatas"][0]

    if not docs:
        refined_output = get_refined_answer(query, "", language)
        return jsonify({"answer": refined_output, "citations": []})

    pairs = [[retrieval_query, doc] for doc in docs]
    scores = reranker.predict(pairs)
    ranked_results = sorted(zip(scores, docs, metas), key=lambda x: x[0], reverse=True)
    top_3_results = ranked_results[:3]

    combined_english_context = ""
    citations = []

    for i, (score, doc, meta) in enumerate(top_3_results, 1):
        chapter = meta.get("chapter", "Unknown Chapter")
        explanation = meta.get("english_text", "Explanation missing.")
        combined_english_context += f"\n--- Source {i} (Chapter: {chapter}) ---\n{explanation}\n"
        citations.append({
            "rank": i,
            "score": round(float(score), 3),
            "sthana": "Charaka Samhita",
            "adhyaya_number": 0,
            "adhyaya_name": chapter,
            "shloka_start": 0,
            "shloka_end": 0,
            "url": "#",
        })

    refined_output = get_refined_answer(query, combined_english_context, language)

    return jsonify({"answer": refined_output, "citations": citations})


# ==========================================
# COMPARE — WEB SEARCH AGENT
# ==========================================
@app.route("/compare", methods=["POST"])
def compare():
    data = request.json
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "No query provided"}), 400
    if not llm:
        return jsonify({"error": "LLM not configured — add GEMINI_API_KEY to .env"}), 500
    if not DDG_AVAILABLE:
        return jsonify({"error": "duckduckgo_search not installed. Run: pip install duckduckgo_search"}), 500

    # Step 1: Extract disease/condition name
    try:
        disease_resp = llm.generate_content(
            f"Extract the specific disease, medical condition, or health ailment the user is asking about. "
            f"Return ONLY the condition name (2-5 words max, in English). Query: {query}"
        )
        disease = disease_resp.text.strip()
    except Exception:
        disease = query

    treatments = {}

    for system in ["Ayurveda", "Homeopathy", "Allopathy"]:
        treatment_snippets = []
        medicine_snippets = []
        price_snippet = ""

        # Step 2: Three focused searches per system
        with DDGS() as ddgs:
            # Search 1: How this system specifically treats the disease
            try:
                r1 = list(ddgs.text(
                    f"best {system} treatment {disease} specific remedies India",
                    max_results=6
                ))
                treatment_snippets = [r.get("body", "") for r in r1]
            except Exception as e:
                print(f"[DDG treatment error — {system}]: {e}")

            # Search 2: Named medicines/herbs/drugs used
            try:
                r2 = list(ddgs.text(
                    f"{system} medicines names for {disease} recommended doctors",
                    max_results=5
                ))
                medicine_snippets = [r.get("body", "") for r in r2]
            except Exception as e:
                print(f"[DDG medicine error — {system}]: {e}")

            # Search 3: Prices
            try:
                r3 = list(ddgs.text(
                    f"cost of {system} treatment {disease} India price per month",
                    max_results=4
                ))
                price_snippet = " ".join([r.get("body", "") for r in r3[:3]])
            except Exception as e:
                print(f"[DDG price error — {system}]: {e}")

        # Step 3: Strict Gemini synthesis
        treatment_context = "\n".join(treatment_snippets)
        medicine_context  = "\n".join(medicine_snippets)

        synth_prompt = f"""You are a medical information expert. Use the web search results below to answer specifically about {system} treatment for {disease}.

=== TREATMENT SEARCH RESULTS ===
{treatment_context[:1200]}

=== MEDICINE NAME SEARCH RESULTS ===
{medicine_context[:1000]}

=== PRICE SEARCH RESULTS ===
{price_snippet[:600]}

Return a JSON object with exactly these fields. Be SPECIFIC — use real named medicines, herbs, or drugs, NOT generic categories:
{{
  "description": "3 sentences: what {system} believes about {disease}, how it treats it, and the main goal of treatment. Be specific to {disease}, not generic.",
  "key_medicines": [
    "Actual named medicine/herb/drug 1 (brief note on what it does)",
    "Actual named medicine/herb/drug 2 (brief note)",
    "Actual named medicine/herb/drug 3 (brief note)",
    "Actual named medicine/herb/drug 4 (brief note)"
  ],
  "approach": "One crisp sentence on {system}'s core philosophy for treating {disease} specifically.",
  "price_range": "Realistic monthly cost in INR based on search results or your knowledge. Give a number range like ₹300–₹1500 per month. Never say varies."
}}

IMPORTANT:
- key_medicines must contain REAL names (e.g. for Ayurveda: Karela, Gurmar, Vijayasar; for Homeopathy: Syzygium jambolanum, Uranium nitricum; for Allopathy: Metformin, Glipizide, Januvia).
- Never use generic terms like "Plant-derived products" or "Mineral-based remedies".
- Return ONLY valid JSON. No markdown, no extra text."""

        try:
            resp = llm.generate_content(synth_prompt)
            synth = parse_llm_json(resp.text)
        except Exception as e:
            print(f"[Gemini synthesis error — {system}]: {e}")
            synth = {
                "description": f"{system} has established protocols for treating {disease}.",
                "key_medicines": [],
                "approach": f"{system} approach to {disease}",
                "price_range": "₹200–₹1000 per month",
            }

        treatments[system.lower()] = {**synth}

    return jsonify({"disease": disease, "query": query, "treatments": treatments})


if __name__ == "__main__":
    app.run(port=8000, debug=True)
