import json
import os
from collections import defaultdict

# Robust paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# analysis/src -> analysis -> root
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "trace-crs-chatbot")
ORIGINAL_EXPORTS_PATH = os.path.join(DATA_PATH, "original_firestore_exports")

print(f"Loading data from {ORIGINAL_EXPORTS_PATH}")
with open(os.path.join(ORIGINAL_EXPORTS_PATH, "conversations.json")) as f:
    conversations = json.load(f)

with open(os.path.join(ORIGINAL_EXPORTS_PATH, "cfe_pipeline_responses.json")) as f:
    cfe_responses = json.load(f)

conversations_by_id = defaultdict(list)
cfe_responses_by_id = defaultdict(list)

# Keywords to filter out sessions (Case Sensitive)
blocked_keywords = ["Ashmi", "Adithi"]

for s in conversations:
    if "feedback_answers" in s:
        # Check if session is invalid based on Q4 answer
        is_invalid_session = False
        for fa in s["feedback_answers"]:
            # Check for q_id 4 (Additional Feedback)
            if fa.get("q_id") == 4:
                answer_text = fa.get("answer", "")
                if any(keyword in answer_text for keyword in blocked_keywords):
                    is_invalid_session = True
                    break
        
        if is_invalid_session:
            print(f"Skipping invalid session {s.get('session_id')} (marked as test via Q4)")
            continue

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

merged_path = os.path.join(DATA_PATH, "merged", "combined_collections.json")
print(f"Writing merged data to {merged_path}:\n valid entries: {len(joined)}")
with open(merged_path, "w") as f:
    json.dump(joined, f, indent=4, ensure_ascii=False)
