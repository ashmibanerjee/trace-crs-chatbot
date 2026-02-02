import matplotlib.pyplot as plt
import os
from plot_utils import (
    load_json, DATA_PATH, OUTPUT_DIR, set_paper_style, save_plot
)

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QUESTIONS_PATH = os.path.join(PROJECT_ROOT, 'frontend', 'feedback_questions.json')

def process_feedback_data(data):
    """Process feedback data and return counts for each question type."""
    # Q0: Relevance (1=Rec, 2=Alt)
    relevance_counts = {1: 0, 2: 0}
    
    # Q1, Q2, Q3: Likert scales (1-5)
    clarity_counts = {i: 0 for i in range(1, 6)}
    explanation_counts = {i: 0 for i in range(1, 6)}
    alternative_counts = {i: 0 for i in range(1, 6)}
    
    total_feedbacks = 0
    
    for session in data:
        for conversation in session.get('conversations', []):
            feedback_answers = conversation.get('feedback_answers')
            if not feedback_answers:
                continue
                
            total_feedbacks += 1
            
            for answer in feedback_answers:
                q_id = answer.get('q_id')
                option_id = answer.get('option_id')
                
                if option_id is None:
                    continue
                    
                if q_id == 0:
                    if option_id in relevance_counts:
                        relevance_counts[option_id] += 1
                elif q_id == 1:
                    if option_id in clarity_counts:
                        clarity_counts[option_id] += 1
                elif q_id == 2:
                    if option_id in explanation_counts:
                        explanation_counts[option_id] += 1
                elif q_id == 3:
                    if option_id in alternative_counts:
                        alternative_counts[option_id] += 1
                        
    return total_feedbacks, relevance_counts, clarity_counts, explanation_counts, alternative_counts

def plot_relevance(counts):
    """Plot Q0: Recommendation Relevance."""
    plt.figure(figsize=(6,6))
    labels = ['Recommended', 'Alternative']
    
    total = sum(counts.values())
    total = total if total > 0 else 1
    values = [counts[1] / total * 100, counts[2] / total * 100]
    
    bars = plt.bar(labels, values, width=0.5, color=['#4CAF50', '#2196F3'])

    plt.ylabel('Percentage of Responses (%)', fontweight='bold')
    plt.ylim(0, 110)
    
    plt.xticks(fontweight='bold')
    plt.yticks(fontweight='bold')

    # Add percentage labels
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=24, fontweight='bold')
    
    save_plot('q0_relevance', 'Preference: Recommended vs Alternative (Q0)')

def plot_combined_likert(clarity_counts, explanation_counts, alternative_counts):
    """Plot combined horizontal stacked bar chart for Q1-Q3."""
    q1_total = sum(clarity_counts.values())
    q2_total = sum(explanation_counts.values())
    q3_total = sum(alternative_counts.values())
    
    # Avoid division by zero
    q1_total = q1_total if q1_total > 0 else 1
    q2_total = q2_total if q2_total > 0 else 1
    q3_total = q3_total if q3_total > 0 else 1
    
    category_labels = [
        "1 - Not at all",
        "2 - Slightly",
        "3 - Moderately",
        "4 - Very well / Strongly",
        "5 - Extremely"
    ]
    
    # Calculate percentages for each series
    q1_pcts = [clarity_counts[i] / q1_total * 100 for i in range(1, 6)]
    q2_pcts = [explanation_counts[i] / q2_total * 100 for i in range(1, 6)]
    q3_pcts = [alternative_counts[i] / q3_total * 100 for i in range(1, 6)]
    
    plt.figure(figsize=(12, 6))
    
    bar_width = 0.5
    indices = range(len(category_labels))
    
    # Plot Q1 (Base)
    plt.barh(indices, q1_pcts, height=bar_width, color='#FFE066', label='Q1: Clarifying Questions Quality')
    
    # Plot Q2 (Stacked on Q1)
    plt.barh(indices, q2_pcts, left=q1_pcts, height=bar_width, color='#66B2FF', label='Q2: Explanation Quality')
    
    # Plot Q3 (Stacked on Q1+Q2)
    left_q3 = [x + y for x, y in zip(q1_pcts, q2_pcts)]
    plt.barh(indices, q3_pcts, left=left_q3, height=bar_width, color='#D8A4B5', label='Q3: Choice Reconsideration Level')
    
    plt.xlabel('Percentage of Responses (%)', fontweight='bold')
    plt.yticks(indices, category_labels, fontweight='bold')
    plt.xticks(fontweight='bold')
    plt.legend()
    
    # Add percentage labels inside bars
    for i, (v1, v2, v3) in enumerate(zip(q1_pcts, q2_pcts, q3_pcts)):
        # Q1 Label
        if v1 > 0:
            plt.text(v1/2, i, f"{v1:.1f}", ha='center', va='center', fontsize=20, fontweight='bold', color='black')
        # Q2 Label
        if v2 > 0:
            plt.text(v1 + v2/2, i, f"{v2:.1f}", ha='center', va='center', fontsize=20, fontweight='bold', color='black')
        # Q3 Label
        if v3 > 0:
            plt.text(v1 + v2 + v3/2, i, f"{v3:.1f}", ha='center', va='center', fontsize=20, fontweight='bold', color='black')
            
    plt.tight_layout()
    save_plot('combined_q1_q3_stacked', 'Combined Feedback Distribution by Rating Category')

def analyze_feedback():
    print(f"Loading data from {DATA_PATH}")
    try:
        data = load_json(DATA_PATH)
    except FileNotFoundError:
        print(f"Error: Data file not found at {DATA_PATH}")
        return

    # Process data
    total, relevance, clarity, explanation, alternative = process_feedback_data(data)
    
    print(f"Total sessions with feedback: {total}")
    print("Relevance Counts:", relevance)
    print("Clarity Counts:", clarity)
    print("Explanation Counts:", explanation)
    print("Alternative Counts:", alternative)

    set_paper_style()
    
    # Generate Plots
    plot_relevance(relevance)
    plot_combined_likert(clarity, explanation, alternative)

    print(f"Plots saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    analyze_feedback()
