import json
from collections import defaultdict

DATA_PATH = "../../data/trace-crs-chatbot/"
ORIGINAL_EXPORTS_PATH = DATA_PATH + "original_firestore_exports/"
with open(ORIGINAL_EXPORTS_PATH + "conversations.json") as f:
    conversations = json.load(f)

with open(ORIGINAL_EXPORTS_PATH + "cfe_pipeline_responses.json") as f:
    cfe_responses = json.load(f)

conversations_by_id = defaultdict(list)
cfe_responses_by_id = defaultdict(list)

for s in conversations:
    conversations_by_id[s["session_id"]].append(s)
for e in cfe_responses:
    cfe_responses_by_id[e["session_id"]].append(e)

all_session_ids = set(conversations_by_id) | set(cfe_responses_by_id)

joined = []

for session_id in all_session_ids:
    joined.append({
        "session_id": session_id,
        "conversations": conversations_by_id.get(session_id, []),
        "cfe_responses": cfe_responses_by_id.get(session_id, [])
    })

with open(DATA_PATH + "merged/combined_collections.json", "w") as f:
    json.dump(joined, f, indent=4, ensure_ascii=False)

