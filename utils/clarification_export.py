"""
Clarification Data Export Utility
Export clarification questions and answers from the database for analysis
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database.config import get_conversation_store


async def export_clarification_data(
    output_file: str = "clarification_data.json",
    days_back: int = 30,
    format: str = "detailed"
) -> Dict[str, Any]:
    """
    Export clarification question/answer pairs from the database
    
    Args:
        output_file: Output filename
        days_back: Number of days to look back
        format: 'detailed' or 'simple'
        
    Returns:
        Dictionary with export statistics
    """
    store = get_conversation_store()
    
    # Get all conversations
    conversations = await store.export_for_training(
        output_format='full',
        limit=10000
    )
    
    clarification_data = []
    total_sessions = 0
    total_qa_pairs = 0
    
    for conv in conversations:
        # Check if conversation has clarification data
        if not conv.get('collected_entities', {}).get('clarification_answers'):
            continue
        
        total_sessions += 1
        session_data = {
            'session_id': conv.get('session_id'),
            'timestamp': conv.get('created_at'),
            'user_type': conv.get('user_type', 'unknown'),
            'original_query': None,
            'clarification_qa': []
        }
        
        # Extract Q&A pairs
        answers = conv['collected_entities']['clarification_answers']
        
        for q_id, qa_data in answers.items():
            total_qa_pairs += 1
            
            if format == 'detailed':
                session_data['clarification_qa'].append({
                    'question_id': q_id,
                    'category': qa_data.get('category', 'unknown'),
                    'question': qa_data.get('question', ''),
                    'answer': qa_data.get('answer', '')
                })
            else:
                session_data['clarification_qa'].append({
                    'q': qa_data.get('question', ''),
                    'a': qa_data.get('answer', '')
                })
        
        # Try to extract original query from conversation history
        for msg in conv.get('conversation_history', []):
            if msg.get('metadata', {}).get('type') == 'clarification_trigger':
                session_data['original_query'] = msg.get('content')
                break
        
        clarification_data.append(session_data)
    
    # Export to file
    export = {
        'export_date': datetime.now().isoformat(),
        'total_sessions': total_sessions,
        'total_qa_pairs': total_qa_pairs,
        'format': format,
        'data': clarification_data
    }
    
    with open(output_file, 'w') as f:
        json.dump(export, f, indent=2)
    
    print(f"✅ Exported {total_sessions} sessions with {total_qa_pairs} Q&A pairs")
    print(f"   Output: {output_file}")
    
    return export


async def get_clarification_statistics() -> Dict[str, Any]:
    """
    Get statistics about clarification usage
    
    Returns:
        Dictionary with various statistics
    """
    store = get_conversation_store()
    
    conversations = await store.export_for_training(
        output_format='full',
        limit=10000
    )
    
    stats = {
        'total_conversations': len(conversations),
        'with_clarification': 0,
        'without_clarification': 0,
        'total_questions_asked': 0,
        'total_answers_collected': 0,
        'category_breakdown': {},
        'completion_rate': 0
    }
    
    clarification_completed = 0
    
    for conv in conversations:
        clarification_answers = conv.get('collected_entities', {}).get('clarification_answers')
        
        if clarification_answers:
            stats['with_clarification'] += 1
            
            # Check if completed
            if conv.get('clarification_complete'):
                clarification_completed += 1
            
            # Count answers
            for q_id, qa_data in clarification_answers.items():
                stats['total_answers_collected'] += 1
                
                category = qa_data.get('category', 'unknown')
                if category not in stats['category_breakdown']:
                    stats['category_breakdown'][category] = 0
                stats['category_breakdown'][category] += 1
        else:
            stats['without_clarification'] += 1
    
    if stats['with_clarification'] > 0:
        stats['completion_rate'] = (clarification_completed / stats['with_clarification']) * 100
    
    return stats


async def print_clarification_report():
    """Print a detailed report of clarification usage"""
    print("=" * 60)
    print("CLARIFICATION FLOW USAGE REPORT")
    print("=" * 60)
    
    stats = await get_clarification_statistics()
    
    print(f"\nTotal Conversations: {stats['total_conversations']}")
    print(f"  With Clarification: {stats['with_clarification']}")
    print(f"  Without Clarification: {stats['without_clarification']}")
    
    if stats['with_clarification'] > 0:
        usage_rate = (stats['with_clarification'] / stats['total_conversations']) * 100
        print(f"  Usage Rate: {usage_rate:.1f}%")
    
    print(f"\nClarification Stats:")
    print(f"  Total Answers Collected: {stats['total_answers_collected']}")
    print(f"  Completion Rate: {stats['completion_rate']:.1f}%")
    
    print(f"\nQuestion Category Breakdown:")
    for category, count in sorted(stats['category_breakdown'].items(), 
                                   key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count}")
    
    print("\n" + "=" * 60)


async def export_for_training(
    output_file: str = "clarification_training_data.jsonl"
):
    """
    Export clarification data in JSONL format for model training
    
    Args:
        output_file: Output filename
    """
    store = get_conversation_store()
    
    conversations = await store.export_for_training(
        output_format='full',
        limit=10000
    )
    
    training_examples = []
    
    for conv in conversations:
        clarification_answers = conv.get('collected_entities', {}).get('clarification_answers')
        
        if not clarification_answers:
            continue
        
        # Extract original query
        original_query = None
        for msg in conv.get('conversation_history', []):
            if msg.get('metadata', {}).get('type') == 'clarification_trigger':
                original_query = msg.get('content')
                break
        
        if not original_query:
            continue
        
        # Create training example
        for q_id, qa_data in clarification_answers.items():
            example = {
                "query": original_query,
                "question_category": qa_data.get('category'),
                "clarifying_question": qa_data.get('question'),
                "user_answer": qa_data.get('answer'),
                "user_type": conv.get('user_type', 'unknown')
            }
            training_examples.append(example)
    
    # Write JSONL
    with open(output_file, 'w') as f:
        for example in training_examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"✅ Exported {len(training_examples)} training examples")
    print(f"   Output: {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "export":
            asyncio.run(export_clarification_data())
        elif command == "stats":
            asyncio.run(print_clarification_report())
        elif command == "training":
            asyncio.run(export_for_training())
        else:
            print(f"Unknown command: {command}")
            print("Usage: python clarification_export.py [export|stats|training]")
    else:
        print("Clarification Data Export Utility")
        print("\nUsage:")
        print("  python clarification_export.py export    - Export all clarification data")
        print("  python clarification_export.py stats     - Show usage statistics")
        print("  python clarification_export.py training  - Export for model training")
