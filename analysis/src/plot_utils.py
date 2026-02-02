import json
import matplotlib.pyplot as plt
import os
import seaborn as sns
import dotenv
import shutil

dotenv.load_dotenv()

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'trace-crs-chatbot', 'merged', 'combined_collections.json')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'plots')
PAPER_LOCATION = os.getenv('PAPER_LOCATION')
PAPER_PLOTS_DIR = os.path.join(PAPER_LOCATION, 'plots') if PAPER_LOCATION else None

def load_json(path):
    """Load JSON data from a file."""
    with open(path, 'r') as f:
        return json.load(f)

def ensure_dir(directory):
    """Ensure that a directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def set_paper_style():
    """Set matplotlib style for publication-quality figures."""
    sns.set_theme(style="whitegrid")
    
    # Paper-quality font settings
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.weight': 'bold',
        'font.size': 20,
        'axes.labelsize': 22,
        'axes.labelweight': 'bold',
        'axes.titlesize': 24,
        'axes.titleweight': 'bold',
        'axes.linewidth': 2.0,
        'axes.labelcolor': 'black',
        'xtick.labelsize': 18,
        'xtick.color': 'black',
        'ytick.labelsize': 18,
        'ytick.color': 'black',
        'text.color': 'black',
        'legend.fontsize': 18,
        'legend.frameon': True,
        'legend.framealpha': 0.9,
        'legend.edgecolor': 'gray',
        'figure.titlesize': 20,
        'lines.linewidth': 2.5,
        'lines.markersize': 8,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
        'grid.alpha': 0.3,
        'figure.max_open_warning': 0
    })

def save_plot(filename_base, title=None):
    """Save plot as both PDF and PNG, and copy to PAPER_PLOTS_DIR if available."""
    ensure_dir(os.path.join(OUTPUT_DIR, "pdf"))
    ensure_dir(os.path.join(OUTPUT_DIR, "png"))
    
    pdf_path = os.path.join(OUTPUT_DIR, "pdf", f"{filename_base}.pdf")
    png_path = os.path.join(OUTPUT_DIR, "png", f"{filename_base}.png")
    
    plt.savefig(pdf_path, bbox_inches='tight', dpi=300)
    
    if PAPER_PLOTS_DIR:
        try:
            ensure_dir(PAPER_PLOTS_DIR)
            shutil.copy(pdf_path, PAPER_PLOTS_DIR)
            print(f"Copied {filename_base}.pdf to {PAPER_PLOTS_DIR}")
        except Exception as e:
            print(f"Error copying to PAPER_PLOTS_DIR: {e}")

    if title:
        plt.title(title, fontweight='bold')
    
    plt.savefig(png_path, bbox_inches='tight', dpi=300)
    plt.close()
