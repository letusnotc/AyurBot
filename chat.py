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
        text_snippets = []
        price_snippet = ""

        # Step 2: Web search for each treatment system — each step is independent
        with DDGS() as ddgs:
            try:
                text_results = list(ddgs.text(f"{system} treatment for {disease}", max_results=5))
                text_snippets = [r.get("body", "") for r in text_results[:4]]
            except Exception as e:
                print(f"[DDG text error — {system}]: {e}")

            # Images are served as static assets from the frontend public folder

            try:
                price_results = list(
                    ddgs.text(f"{system} medicine price {disease} India", max_results=3)
                )
                price_snippet = " ".join([r.get("body", "") for r in price_results[:2]])
            except Exception as e:
                print(f"[DDG price error — {system}]: {e}")

        # Step 3: Synthesize with Gemini
        context = "\n".join(text_snippets)
        synth_prompt = f"""Based on these search results about {system} treatment for {disease}:

{context}

Price context (from pharmacy search): {price_snippet[:700]}

Return a JSON object with exactly these fields:
{{
  "description": "2-3 sentence clear overview of how {system} treats or manages {disease}",
  "key_medicines": ["medicine 1", "medicine 2", "medicine 3", "medicine 4"],
  "approach": "One-line philosophy of this treatment system for this condition",
  "price_range": "Approximate cost in INR — extract from price context above if available, otherwise use your own knowledge to give a realistic typical range (e.g. ₹80–₹300 per month). Never say 'Varies by provider' — always give a number range."
}}

Return ONLY valid JSON. No markdown code fences, no extra text."""

        try:
            resp = llm.generate_content(synth_prompt)
            synth = parse_llm_json(resp.text)
        except Exception as e:
            print(f"[Gemini synthesis error — {system}]: {e}")
            synth = {
                "description": f"{system} has established protocols for treating {disease}. Consult a qualified practitioner for personalized guidance.",
                "key_medicines": [],
                "approach": f"Traditional {system} approach",
                "price_range": "Varies by provider",
            }

        treatments[system.lower()] = {**synth}

    return jsonify({"disease": disease, "query": query, "treatments": treatments})


if __name__ == "__main__":
    app.run(port=8000, debug=True)
