import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

print("Loading embedding model...")
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

# We use a brand new directory to keep our clean data isolated from the old database
DB_DIR = "./charaka_paired_db"
client = chromadb.Client(
    Settings(
        persist_directory=DB_DIR,
        is_persistent=True
    )
)

collection_name = "charaka_samhita_paired"

# Start with a clean slate
try:
    client.delete_collection(collection_name)
    print("Cleared old collection.")
except:
    pass

collection = client.create_collection(collection_name)
print("New collection 'charaka_samhita_paired' created.")

print("Loading paired chunks...")
with open("charaka_preprocessed/charaka_paired_chunks.json", "r", encoding="utf8") as f:
    chunks = json.load(f)

print(f"Total chunks to embed: {len(chunks)}")

BATCH_SIZE = 5000

for start in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[start:start + BATCH_SIZE]
    
    texts_to_embed = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(batch):
        # We embed the English explanation for the semantic search to trigger on
        embed_text = f"Chapter: {chunk['chapter']} - {chunk['english']}"
        texts_to_embed.append(embed_text)

        # The MAGIC happens here: We store BOTH the Shloka and the English in the metadata
        metadatas.append({
            "chapter": chunk["chapter"],
            "sanskrit_text": chunk["sanskrit"],
            "english_text": chunk["english"]
        })

        ids.append(f"chunk_{start + i}")

    print(f"\nEmbedding batch {start} to {start + len(batch)}... (This might take a few minutes)")
    embeddings = model.encode(texts_to_embed).tolist()

    collection.add(
        documents=texts_to_embed,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Successfully inserted batch.")

print("\n==============================")
print("Vector DB Created Successfully!")
print(f"Saved in folder: {DB_DIR}")