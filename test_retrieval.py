from rag.pipeline import get_vector_store
from rag.retriever import retrieve

store = get_vector_store()
query = "What is PaySphere?"
chunks = retrieve(query, store)

for i, c in enumerate(chunks):
    print(f"\n--- Chunk {i+1} ---")
    print(c.get('text', ''))
