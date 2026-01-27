import json
import os
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import seaborn as sns

# Set paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

INPUT_FILE= os.path.join(PROJECT_ROOT, 'data', 'trace-crs-chatbot', 'merged', 'combined_collections.json')
OUTPUT_DIR = os.path.join(PROJECT_ROOT,'data', 'trace-crs-chatbot', 'results')


os.makedirs(OUTPUT_DIR, exist_ok=True)
def to_str(x):
    if isinstance(x, list):
        return " ".join(map(str, x))
    return str(x)

def load_data(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def extract_persona_explanation_pairs(data):
    pairs = []
    for session in data:
        for cfe in session.get('cfe_responses', []):
            context = cfe.get('context')
            if not context:
                continue
                
            intent_classification = context.get('intent_classification')
            if not intent_classification:
                continue
                
            persona = intent_classification.get('user_travel_persona')
            explanation = cfe.get('explanation_shown')
            travel_intent = intent_classification.get('travel_intent')
            alternative_explanations = cfe.get('alternative_explanation')
            alternative_shown = cfe.get('alternative_recommendation')
            
            if persona and explanation:
                pairs.append({
                    'session_id': session.get('session_id'),
                    'persona': persona,
                    'travel_intent': travel_intent,
                    'explanation': explanation,
                    'recommendation': cfe.get('recommendation_shown'),
                    'alternative_shown': alternative_shown,
                    'alternative_explanation': alternative_explanations
                })
    return pairs

def run_correlation_analysis():
    print("Loading data...")
    data = load_data(INPUT_FILE)
    pairs = extract_persona_explanation_pairs(data)
    
    if not pairs:
        print("No valid persona-explanation pairs found.")
        return

    df = pd.DataFrame(pairs)
    print(f"Extracted {len(df)} pairs for analysis.")

    print("Initializing Sentence Transformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    df ["input"] = df['travel_intent'] + " " + df['persona']
    # df["output"] = (
    #         df["recommendation"].apply(to_str) + " " +
    #         df["explanation"].apply(to_str) + " " +
    #         df["alternative_shown"].apply(to_str) + " " +
    #         df["alternative_explanation"].apply(to_str)
    # )
    df["output"] = (
            df["recommendation"].apply(to_str) + " " +
            df["explanation"].apply(to_str) + " "
            # df["alternative_shown"].apply(to_str) + " " +
            # df["alternative_explanation"].apply(to_str)
    )
    print("Generating embeddings for personas...")
    input_embeddings = model.encode(df['input'].tolist(), show_progress_bar=True)
    
    print("Generating embeddings for explanations...")
    explanation_embeddings = model.encode(df['output'].tolist(), show_progress_bar=True)

    print("Calculating cosine similarities...")
    similarities = []
    for i in range(len(df)):
        sim = cosine_similarity(
            input_embeddings[i].reshape(1, -1),
            explanation_embeddings[i].reshape(1, -1)
        )[0][0]
        similarities.append(sim)

    df['similarity_score'] = similarities

    # Save results
    results_path = os.path.join(OUTPUT_DIR, 'persona_explanation_similarity.csv')
    df.drop(columns=['input', 'output'], inplace=True)
    df.to_csv(results_path, index=False)
    print(f"Results saved to {results_path}")

    # Plotting
    plt.figure(figsize=(10, 6))
    sns.histplot(df['similarity_score'], bins=20, kde=True, color='skyblue')
    plt.title('Semantic Similarity: User Persona vs. Recommendation Explanation')
    plt.xlabel('Cosine Similarity Score')
    plt.ylabel('Frequency')
    plt.grid(axis='y', alpha=0.3)
    
    plot_path = os.path.join(OUTPUT_DIR, 'persona_explanation_similarity_dist.png')
    plt.savefig(plot_path)
    print(f"Distribution plot saved to {plot_path}")

    # Statistics
    print("\n--- Similarity Statistics ---")
    print(df['similarity_score'].describe())
    
    # Top 3 most aligned sessions
    print("\nTop 3 Most Aligned Sessions:")
    print(df.nlargest(3, 'similarity_score')[['session_id', 'similarity_score', 'recommendation']])

    # Bottom 3 least aligned sessions
    print("\nBottom 3 Least Aligned Sessions:")
    print(df.nsmallest(3, 'similarity_score')[['session_id', 'similarity_score', 'recommendation']])

if __name__ == "__main__":
    run_correlation_analysis()
