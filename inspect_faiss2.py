import pickle

try:
    with open('d:/data/vector_index/index.meta', 'rb') as f:
        metadata = pickle.load(f)
        print(f"Total chunks: {len(metadata)}")
        for m in metadata[:5]:
            text = m.get('text', '')[:200]
            print(f"-- {m.get('filename')}: {text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')}")
except Exception as e:
    print(f"Error: {e}")
