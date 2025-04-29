import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load the CSV file
file_path = "Session_20250418-113313_SSE_export.csv"
df = pd.read_csv(file_path)

# Select and clean relevant columns
df_clean = df[['humidity', 'width']].dropna()

# Set Seaborn style for publication
sns.set(style="whitegrid", context="talk")

# Create the scatter plot
plt.figure(figsize=(8, 6))
sns.scatterplot(
    x='humidity',
    y='width',
    data=df_clean,
    s=80,
    color='dodgerblue',
    edgecolor='black'
)

# Add labels and title
plt.title('Relationship Between Humidity and Layer Width', fontsize=16)
plt.xlabel('Humidity (%)', fontsize=14)
plt.ylabel('Layer Width (mm)', fontsize=14)

# Set y-axis to start from 30
plt.ylim(bottom=30)

# Add additional plot info
plt.text(
    x=df_clean['humidity'].max(),  # far right
    y=df_clean['width'].max(),     # near top
    s="Print Speed = 100 mm/min\nLayer Height = 15 mm",
    fontsize=12,
    ha='right',
    va='top',
    bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3')
)

# Enable grid
plt.grid(True, which='both', linestyle='--', linewidth=0.5)

# Layout and save
plt.tight_layout()
plt.savefig('humidity_vs_layer_width_plot_annotated.png', dpi=300)
plt.show()
