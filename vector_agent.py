import chromadb
from sentence_transformers import SentenceTransformer

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Chroma client (local DB)
client = chromadb.Client()
collection = client.get_or_create_collection(name="orders_notes")

def add_documents(texts, metadatas=None):
    embeddings = model.encode(texts).tolist()
    ids = [str(i) for i in range(len(texts))]
    collection.add(documents=texts, embeddings=embeddings, ids=ids, metadatas=metadatas)


def search(query, top_k=3):
    embedding = model.encode([query]).tolist()
    results = collection.query(query_embeddings=embedding, n_results=top_k)
    return results
