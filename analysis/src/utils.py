import json
import os
import re
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import ssl

# Fix for SSL certificate verify failed when downloading NLTK data
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download necessary NLTK data
def download_nltk_data():
    resources = [
        'punkt',
        'stopwords',
        'wordnet',
        'punkt_tab',
        'averaged_perceptron_tagger_eng'
    ]
    for resource in resources:
        try:
            nltk.download(resource, quiet=True)
        except Exception as e:
            print(f"Failed to download {resource}: {e}")

download_nltk_data()

def preprocess_text(text):
    if not text or not isinstance(text, str):
        return ""

    # 1. Lowercase and remove conversational filler phrases
    text = text.lower()
    fillers = [
        r"i recommend", r"based on your interest in", r"you might like",
        r"sure, i can help", r"here is a", r"i found", r"it seems like",
        r"according to your", r"i've selected", r"looking at your preferences"
    ]
    for filler in fillers:
        text = re.sub(filler, "", text)

    # 2. Tokenize and remove punctuation/numbers
    try:
        tokens = word_tokenize(text)
    except LookupError:
        # Fallback if punkt fails
        tokens = text.split()
        
    tokens = [t for t in tokens if t.isalpha()]

    # 3. Remove stopwords
    try:
        stop_words = set(stopwords.words('english'))
        tokens = [t for t in tokens if t not in stop_words]
    except LookupError:
        pass

    # 4. POS Tagging and filtering (keep Nouns, Adjectives, Verbs)
    try:
        tagged = nltk.pos_tag(tokens)
        tokens = [word for word, tag in tagged if any(tag.startswith(p) for p in ['NN', 'JJ', 'VB'])]
    except LookupError:
        # If POS tagging fails, just keep the tokens as is (filtered by stop words)
        pass

    # 5. Lemmatization
    try:
        lemmatizer = WordNetLemmatizer()
        tokens = [lemmatizer.lemmatize(t) for t in tokens]
    except LookupError:
        pass

    return " ".join(tokens)

def extract_ic_evaluation_data(data):
    """
    Extracts data for Intent Classification (IC) evaluation:
    - User Query + Clarifying Questions + Answers
    - Explanation shown
    - Alternative explanation
    """
    extracted = []
    for session in data:
        for cfe in session.get('cfe_responses', []):
            context = cfe.get('context')
            if not context:
                continue
            ic = context.get('intent_classification')
            if not ic:
                continue
            input_data_list = ic.get('input_data', [])
            
            if not input_data_list:
                continue
                
            input_data = input_data_list[0]
            user_query = input_data.get('user_query', '')
            cqs = input_data.get('clarified_qa', [])
            
            # Combine user query, clarifying questions and answers
            conversation_text = user_query
            for cq in cqs:
                q = cq.get('question', '')
                a = cq.get('answer', '')
                conversation_text += f" {q} {a}"
                
            explanation_shown = cfe.get('explanation_shown', '')
            alt_explanation = cfe.get('alternative_explanation', '')

            persona = ic.get('user_travel_persona')
            travel_intent = ic.get('travel_intent')
            
            # Alternative explanation can be a list or a string
            if isinstance(alt_explanation, list):
                alt_explanation = " ".join(map(str, alt_explanation))
            
            extracted.append({
                'session_id': session.get('session_id'),
                'conversation_text': conversation_text,
                'explanation_shown': explanation_shown,
                'alternative_explanation': alt_explanation,
                'persona': persona,
                'travel_intent': travel_intent
            })
    return extracted

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


def load_data(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return []
    with open(file_path, 'r') as f:
        return json.load(f)
