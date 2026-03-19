import os
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer, CrossEncoder
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load environment variables
load_dotenv()

# ==========================================
# 1. SETUP GENERATIVE LLM
# ==========================================
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    llm = genai.GenerativeModel('gemini-2.5-flash') 
else:
    llm = None
    print("\n[WARNING] No API key provided in .env. Ayurbot will skip the 'Refined Form' generation.")

# ==========================================
# 2. SETUP RETRIEVAL MODELS & DATABASE
# ==========================================
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

def get_refined_answer(query, combined_context):
    """Passes context to the LLM for a synthesized summary with fallback reasoning."""
    if not llm:
        return "Please add your API key to .env to generate refined answers."
        
    if combined_context.strip():
        context_section = f"### CONTEXT FROM DATABASE:\n{combined_context}"
    else:
        context_section = "### NOTE: No direct context was found in the database. Use your internal knowledge of Charaka Samhita to answer, provided the query is Ayurvedic."

    prompt = f"""
    You are Ayurbot, an expert Ayurvedic AI assistant with deep knowledge of the Charaka Samhita.
    A user has asked: "{query}"
    
    {context_section}
    
    STRICT GUIDELINES:
    1. If the query is related to Ayurveda (medicine, herbs, philosophy, lifestyle, etc.), provide a thorough and refined answer.
    2. If the query is NOT related to Ayurveda, politely state that you can only assist with Ayurvedic knowledge.
    3. If database context is provided, prioritize it. If not, use your internal knowledge of ancient scriptures.
    4. MANDATORY: At the very end of your response, provide the single most relevant Sanskrit Shloka (IN DEVANAGARI SCRIPT) from the Charaka Samhita that describes or justifies the answer. Include its English translation and label it as: "### 📜 Relevant Shloka".
    5. Use markdown (bold, bullets) to make your response structured and beautiful.
    """
    
    try:
        response = llm.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating refined answer: {e}"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query')
    top_k = data.get('top_k', 5)

    if not query:
        return jsonify({"error": "No query provided"}), 400

    # STEP 1: Fast Vector Retrieval
    query_embedding = embed_model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=15
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]

    # STEP 2: Handle Empty Results or Proceed to Reranking
    if not docs:
        # Fallback to LLM with no context
        refined_output = get_refined_answer(query, "")
        return jsonify({
            "answer": refined_output,
            "citations": []
        })

    # Cross-Encoder Reranking
    pairs = [[query, doc] for doc in docs]
    scores = reranker.predict(pairs)

    ranked_results = sorted(zip(scores, docs, metas), key=lambda x: x[0], reverse=True)
    
    # STEP 3: Grab the Top 3 best matching chunks
    top_3_results = ranked_results[:3]
    
    combined_english_context = ""
    citations = []
    
    for i, (score, doc, meta) in enumerate(top_3_results, 1):
        chapter = meta.get("chapter", "Unknown Chapter")
        shloka = meta.get("sanskrit_text", "Shloka missing.")
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
            "url": "#"
        })
    
    # STEP 4: Generate the synthesized answer
    refined_output = get_refined_answer(query, combined_english_context)
    
    return jsonify({
        "answer": refined_output,
        "citations": citations
    })

if __name__ == "__main__":
    app.run(port=8000, debug=True)