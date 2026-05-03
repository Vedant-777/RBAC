from pymongo import MongoClient
c = MongoClient('mongodb+srv://tlet34366_db_user:O3eKW6MTSkRuirGj@cluster0.crbbxaq.mongodb.net/?appName=Cluster0')
db = c['intellifusion']
count = db['documents'].count_documents({})
print(f"Documents in MongoDB: {count}")
for d in db['documents'].find({}, {'content': 0}):
    print(f"  - {d['_id']}: {d['filename']}")
c.close()
