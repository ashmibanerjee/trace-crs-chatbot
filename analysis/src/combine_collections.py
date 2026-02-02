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

print(f"Saving original {len(joined)} sessions after filtering out alpha testers...")
with open(DATA_PATH + "merged/combined_collections.json", "w") as f:
    json.dump(joined, f, indent=4, ensure_ascii=False)

# skip Ashmi and Adithi responses 
filtered_cfe_responses = []
for session in joined: 
    try:
        feedback = session['conversations'][0].get('feedback_answers', {})
        for feedback_q in feedback:
            if feedback_q.get('q_id') == 4:
                ans = feedback_q.get('answer')
                for name in ['Ashmi', 'Adithi']: 
                    if name.lower() in ans.lower():
                        session['skip'] = True

        if session.get('skip'): 
            print(f"Skipping session {session['session_id']} due to alpha tester feedback...")
            continue
        else: 
            session['skip'] = False
            filtered_cfe_responses.append(session)
    
    except Exception as e:
        # No conversations found
        print(f"Error processing session {session['session_id']}: {e}")

print(f"Saving {len(filtered_cfe_responses)} sessions after filtering out alpha testers...")
with open(DATA_PATH + "merged/combined_collections_filtered.json", "w") as f:
    json.dump(filtered_cfe_responses, f, indent=4, ensure_ascii=False)

