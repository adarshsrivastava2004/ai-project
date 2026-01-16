from vector_agent import add_documents

texts = [
    "Customer complained about late delivery",
    "Very happy with fast service",
    "Asked for refund due to damaged product",
    "Delivery was delayed but resolved",
    "Customer wants replacement",
    "Great experience, will order again"
]

metadatas = [
    {"type": "complaint"},
    {"type": "positive"},
    {"type": "refund"},
    {"type": "complaint"},
    {"type": "replacement"},
    {"type": "positive"}
]

add_documents(texts, metadatas)

print("Vector data added")
