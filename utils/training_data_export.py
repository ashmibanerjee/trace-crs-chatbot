"""
Training Data Export Utilities
Convert conversation history to various training formats
"""
from typing import Dict, Any, List
import json
from datetime import datetime


def export_conversation_as_jsonl(
    conversation_history: List[Dict[str, Any]],
    session_metadata: Dict[str, Any] = None
) -> str:
    """
    Export conversation history as JSONL (one JSON object per line)
    Compatible with OpenAI fine-tuning format and standard LLM training
    
    Args:
        conversation_history: List of conversation turns with role/content/metadata
        session_metadata: Optional session-level metadata
    
    Returns:
        JSONL formatted string
    """
    lines = []
    
    # Group messages into conversation turns (user + assistant pairs)
    i = 0
    while i < len(conversation_history):
        if conversation_history[i]['role'] == 'user':
            turn = {
                'messages': [
                    {
                        'role': 'user',
                        'content': conversation_history[i]['content']
                    }
                ]
            }
            
            # Add assistant response if available
            if i + 1 < len(conversation_history) and conversation_history[i + 1]['role'] == 'assistant':
                turn['messages'].append({
                    'role': 'assistant',
                    'content': conversation_history[i + 1]['content']
                })
                
                # Add metadata
                turn['metadata'] = {
                    'timestamp': conversation_history[i]['timestamp'],
                    'agent_name': conversation_history[i + 1]['metadata'].get('agent_name'),
                    'action': conversation_history[i + 1]['metadata'].get('action'),
                    'intent': conversation_history[i + 1]['metadata'].get('intent')
                }
                
                i += 2
            else:
                i += 1
            
            lines.append(json.dumps(turn))
    
    return '\n'.join(lines)


def export_conversation_as_qa_pairs(
    conversation_history: List[Dict[str, Any]],
    include_metadata: bool = True
) -> List[Dict[str, Any]]:
    """
    Export conversation as Q&A pairs for supervised learning
    
    Args:
        conversation_history: List of conversation turns
        include_metadata: Whether to include metadata in output
    
    Returns:
        List of Q&A pairs with optional metadata
    """
    qa_pairs = []
    
    i = 0
    while i < len(conversation_history):
        if conversation_history[i]['role'] == 'user':
            qa_pair = {
                'question': conversation_history[i]['content'],
                'timestamp': conversation_history[i]['timestamp']
            }
            
            # Add answer if available
            if i + 1 < len(conversation_history) and conversation_history[i + 1]['role'] == 'assistant':
                qa_pair['answer'] = conversation_history[i + 1]['content']
                
                if include_metadata:
                    qa_pair['metadata'] = {
                        'question_length': conversation_history[i]['metadata'].get('message_length'),
                        'entities_mentioned': conversation_history[i]['metadata'].get('entities_mentioned', []),
                        'agent_name': conversation_history[i + 1]['metadata'].get('agent_name'),
                        'action_type': conversation_history[i + 1]['metadata'].get('action'),
                        'intent': conversation_history[i + 1]['metadata'].get('intent'),
                        'recommendations_count': conversation_history[i + 1]['metadata'].get('recommendations_provided', 0),
                        'clarification_required': conversation_history[i + 1]['metadata'].get('clarification_required', False)
                    }
                
                i += 2
            else:
                qa_pair['answer'] = None
                i += 1
            
            qa_pairs.append(qa_pair)
    
    return qa_pairs


def export_conversation_as_chat_ml(
    conversation_history: List[Dict[str, Any]],
    system_prompt: str = "You are a sustainable tourism assistant helping users find eco-friendly travel destinations."
) -> List[Dict[str, str]]:
    """
    Export conversation in ChatML format (OpenAI/Anthropic style)
    
    Args:
        conversation_history: List of conversation turns
        system_prompt: System prompt to prepend
    
    Returns:
        List of messages in ChatML format
    """
    messages = [
        {'role': 'system', 'content': system_prompt}
    ]
    
    for turn in conversation_history:
        messages.append({
            'role': turn['role'],
            'content': turn['content']
        })
    
    return messages


def export_session_for_training(
    session_data: Dict[str, Any],
    format: str = 'qa_pairs'
) -> Any:
    """
    Export entire session in specified format for model training
    
    Args:
        session_data: Complete session state dictionary
        format: Output format ('qa_pairs', 'jsonl', 'chatml', or 'full')
    
    Returns:
        Formatted training data
    """
    conversation_history = session_data.get('conversation_history', [])
    
    if format == 'qa_pairs':
        return export_conversation_as_qa_pairs(conversation_history)
    
    elif format == 'jsonl':
        return export_conversation_as_jsonl(conversation_history, session_data.get('metadata'))
    
    elif format == 'chatml':
        return export_conversation_as_chat_ml(conversation_history)
    
    elif format == 'full':
        # Full session data including all metadata for analysis
        return {
            'session_id': session_data.get('id'),
            'created_at': session_data.get('created_at'),
            'user_type': session_data.get('user_type'),
            'user_type_confidence': session_data.get('user_type_confidence'),
            'preferences': session_data.get('preferences'),
            'collected_entities': session_data.get('collected_entities'),
            'conversation_history': conversation_history,
            'metadata': session_data.get('metadata'),
            'statistics': {
                'total_turns': len(conversation_history) // 2,
                'total_messages': len(conversation_history),
                'clarifications_needed': session_data.get('metadata', {}).get('clarification_count', 0),
                'intents_detected': session_data.get('metadata', {}).get('intents', [])
            }
        }
    
    else:
        raise ValueError(f"Unknown format: {format}. Use 'qa_pairs', 'jsonl', 'chatml', or 'full'")


def batch_export_sessions(
    sessions: List[Dict[str, Any]],
    output_file: str,
    format: str = 'jsonl'
):
    """
    Batch export multiple sessions to a file
    
    Args:
        sessions: List of session data dictionaries
        output_file: Path to output file
        format: Export format
    """
    with open(output_file, 'w') as f:
        for session in sessions:
            exported = export_session_for_training(session, format)
            
            if format == 'jsonl':
                # Already in JSONL format (multiple lines)
                f.write(exported + '\n')
            else:
                # Write as single JSON object per session
                f.write(json.dumps(exported) + '\n')
    
    print(f"✅ Exported {len(sessions)} sessions to {output_file}")


# Example usage
if __name__ == "__main__":
    # Example conversation history
    sample_history = [
        {
            'role': 'user',
            'content': 'I want to find a sustainable destination',
            'timestamp': '2024-01-01T10:00:00',
            'metadata': {'message_length': 40, 'entities_mentioned': []}
        },
        {
            'role': 'assistant',
            'content': 'I can help you find eco-friendly destinations! What type of environment do you prefer?',
            'timestamp': '2024-01-01T10:00:01',
            'metadata': {
                'agent_name': 'clarification',
                'action': 'CLARIFY',
                'intent': 'FIND_DESTINATION',
                'recommendations_provided': 0,
                'clarification_required': True
            }
        },
        {
            'role': 'user',
            'content': 'I love tropical beaches and nature',
            'timestamp': '2024-01-01T10:00:30',
            'metadata': {'message_length': 35, 'entities_mentioned': ['interests']}
        },
        {
            'role': 'assistant',
            'content': 'Here are my top sustainable recommendations: Costa Rica Eco-Lodge...',
            'timestamp': '2024-01-01T10:00:32',
            'metadata': {
                'agent_name': 'recommendation',
                'action': 'RECOMMEND',
                'intent': 'FIND_DESTINATION',
                'recommendations_provided': 2,
                'clarification_required': False
            }
        }
    ]
    
    print("=== Q&A Pairs Format ===")
    qa_pairs = export_conversation_as_qa_pairs(sample_history)
    print(json.dumps(qa_pairs, indent=2))
    
    print("\n=== JSONL Format ===")
    jsonl = export_conversation_as_jsonl(sample_history)
    print(jsonl)
    
    print("\n=== ChatML Format ===")
    chatml = export_conversation_as_chat_ml(sample_history)
    print(json.dumps(chatml, indent=2))
