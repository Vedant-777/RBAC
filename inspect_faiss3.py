import pickle
import json

try:
    with open('d:/data/vector_index/index.meta', 'rb') as f:
        metadata = pickle.load(f)
        out = []
        for m in metadata[:10]:
            out.append({
                'filename': m.get('filename'),
                'text': m.get('text', '')[:300]
            })
        with open('d:/app/meta_out.json', 'w', encoding='utf-8') as out_f:
            json.dump(out, out_f, indent=2)
except Exception as e:
    print(f"Error: {e}")
