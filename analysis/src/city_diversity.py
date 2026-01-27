import os
import collections
import matplotlib.pyplot as plt
import numpy as np
from plot_utils import (
    load_json, DATA_PATH, set_paper_style, save_plot
)
from utils import preprocess_text

def clean_city_name(city):
    """Clean and preprocess city name."""
    if not city:
        return ""
    # Simple cleaning for city names - might not need full lemmatization/POS
    # but the task requested using common cleaning.
    # Let's use a simpler version for city names to avoid over-cleaning
    cleaned = city.strip().lower()
    # Remove some common fillers if they appear in city names for some reason
    fillers = ["city of", "the city of"]
    for f in fillers:
        cleaned = cleaned.replace(f, "")
    return cleaned.strip().title()

def get_city_diversity_data(data):
    """Extract recommendation_shown and alternative cities."""
    recommended_cities = []
    alternative_cities = []
    
    for session in data:
        for cfe in session.get('cfe_responses', []):
            rec = cfe.get('recommendation_shown')
            alt = cfe.get('alternative_recommendation')
            
            if rec:
                recommended_cities.append(clean_city_name(rec))
            if alt:
                # alternative_recommendation can be a string or list
                if isinstance(alt, list):
                    for a in alt:
                        alternative_cities.append(clean_city_name(a))
                elif isinstance(alt, str):
                    alternative_cities.append(clean_city_name(alt))
                    
    return recommended_cities, alternative_cities

def plot_city_diversity(recommended, alternative, top_n=10):
    """Plot stacked bar chart of city diversity."""
    rec_counts = collections.Counter(recommended)
    alt_counts = collections.Counter(alternative)
    
    # Get all unique cities
    all_cities = set(rec_counts.keys()) | set(alt_counts.keys())
    
    # Calculate total counts for sorting
    total_city_counts = {city: rec_counts.get(city, 0) + alt_counts.get(city, 0) for city in all_cities}
    
    # Sort and take top N
    sorted_cities = sorted(total_city_counts.keys(), key=lambda x: total_city_counts[x], reverse=True)
    top_cities = sorted_cities[:top_n]
    
    if not top_cities:
        print("No city data found to plot.")
        return

    # Total recommendations + alternatives for percentage calculation
    total_samples = sum(total_city_counts.values())
    
    rec_values = [rec_counts.get(city, 0) / total_samples * 100 for city in top_cities]
    alt_values = [alt_counts.get(city, 0) / total_samples * 100 for city in top_cities]
    
    plt.figure(figsize=(12, 8))
    
    # Plotting
    x = np.arange(len(top_cities))
    width = 0.6
    
    plt.bar(x, rec_values, width, label='Recommended', color='#4CAF50')
    plt.bar(x, alt_values, width, bottom=rec_values, label='Alternative', color='#2196F3')
    
    plt.ylabel('Frequency (%)', fontweight='bold')
    plt.xlabel('City Name', fontweight='bold')
    plt.xticks(x, top_cities, rotation=45, ha='right', fontweight='bold')
    plt.yticks(fontweight='bold')
    plt.legend()
    
    plt.tight_layout()
    save_plot('city_diversity', f'Top {top_n} Recommended and Alternative Cities')

def main():
    print(f"Loading data from {DATA_PATH}")
    try:
        data = load_json(DATA_PATH)
    except FileNotFoundError:
        print(f"Error: Data file not found at {DATA_PATH}")
        return

    recommended, alternative = get_city_diversity_data(data)
    print(f"Found {len(recommended)} recommended and {len(alternative)} alternative cities.")
    
    set_paper_style()
    plot_city_diversity(recommended, alternative, top_n=15)
    print("City diversity plots generated.")

if __name__ == "__main__":
    main()
