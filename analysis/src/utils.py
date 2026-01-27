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
