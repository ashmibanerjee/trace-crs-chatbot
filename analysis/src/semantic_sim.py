import os
from typing import Any
import numpy as np
import pandas as pd
from pandas import DataFrame
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from analysis.src.utils import extract_ic_evaluation_data, preprocess_text, load_data

# Set paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

INPUT_FILE = os.path.join(PROJECT_ROOT, 'data', 'trace-crs-chatbot', 'merged', 'combined_collections.json')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'data', 'trace-crs-chatbot', 'results')

os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_evaluation():
    """
    Q + CQ vs CFE
    """
    print("Loading data...")
    data = load_data(INPUT_FILE)
    extracted_data = extract_ic_evaluation_data(data)
    
    if not extracted_data:
        print("No valid IC evaluation data found.")
        return

    df = pd.DataFrame(extracted_data)
    print(f"Extracted {len(df)} samples for analysis.")

    print("Initializing Sentence Transformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print("Preprocessing text...")
    df['conversation_clean'] = df['conversation_text'].apply(preprocess_text)
    df['explanation_clean'] = df['explanation_shown'].apply(preprocess_text)
    df['alt_explanation_clean'] = df['alternative_explanation'].apply(preprocess_text)
    df ['persona_clean'] = df['persona'].apply(preprocess_text)
    df ['travel_intent_clean'] = df['travel_intent'].apply(preprocess_text)
    df ["intent_classifier_clean"] = df["persona_clean"] + " " + df["travel_intent_clean"]
    # Combine explanations for comparison if desired, 
    # but usually we want to see similarity to what was shown.
    # The request asks for similarity between (query+cqs+as) AND (explanation shown + alternative explanation)
    df['total_explanation'] = df['explanation_shown'] + " " + df['alternative_explanation']
    df['total_explanation_clean'] = df['explanation_clean'] + " " + df['alt_explanation_clean']

    df["lorem_ipsum"] = "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum."
    similarities = generate_similarity(df, model, col1 = "conversation_clean", col2="lorem_ipsum")
    print (f"Mean similarity between Conversations (C+CQA) and Lorem Ipsum: {np.mean(similarities):.4f} ({np.std(similarities):.4f}) ")

    similarities = generate_similarity(df, model, col1 = "total_explanation_clean", col2="conversation_clean")

    print(f"Mean similarity between Conversations (C+CQA) and Explanations (CFE + AE): {np.mean(similarities):.4f} ({np.std(similarities):.4f}) ")

    similarities = generate_similarity(df, model, col1 = "conversation_clean", col2="intent_classifier_clean")
    print(f"Mean similarity between Conversations (Q+CQA) and Intent Classifier (IC: persona + travel_intent): {np.mean(similarities):.4f} ({np.std(similarities):.4f}) ")

    similarities = generate_similarity(df, model, col1 = "intent_classifier_clean", col2="total_explanation_clean")
    print(f"Mean similarity between Intent Classifier (IC: persona + travel_intent) and Explanations (CFE + AE): {np.mean(similarities):.4f} ({np.std(similarities):.4f}) ")

def generate_similarity(df: DataFrame, model: SentenceTransformer, col1:str = "", col2:str = "") -> list[Any]:
    print("Generating embeddings (Cleaned)...")
    conv_embeddings = model.encode(df[col1].tolist(), show_progress_bar=True)
    exp_embeddings = model.encode(df[col2].tolist(), show_progress_bar=True)

    print("Calculating cosine similarities...")
    similarities = []
    for i in range(len(df)):
        sim = cosine_similarity(
            conv_embeddings[i].reshape(1, -1),
            exp_embeddings[i].reshape(1, -1)
        )[0][0]
        similarities.append(sim)
    return similarities





if __name__ == "__main__":
    run_evaluation()
