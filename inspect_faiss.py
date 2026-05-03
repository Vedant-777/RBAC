import pickle
import os

try:
    with open('data/vector_index/index.faiss.pkl', 'rb') as f:
        data = pickle.load(f)
        print(f"Total chunks: {len(data['metadata'])}")
        for m in data['metadata'][:5]:
            print(f"-- {m.get('filename')}: {m.get('text', '')[:200]}")
except Exception as e:
    print(f"Error: {e}")
