# import pandas as pd
# import matplotlib.pyplot as plt

# # Load CSVs
# corr = pd.read_csv('SLP_correction.csv')
# no_corr = pd.read_csv('SLP_no_correction.csv')

# # Extract actual distances in CSV
# # (Assuming your CSV distance goes approx 0 → 1000)
# distance_values = corr['distance'].values

# # Choose sample distances similar to your example
# sample_distances = [0, 200, 400, 600, 800, 1000]

# # Function: find nearest height at each sample point
# def sample_nearest(df, height_col):
#     results = []
#     for target in sample_distances:
#         idx = (df['distance'] - target).abs().idxmin()
#         results.append(df.loc[idx, height_col])
#     return results

# # Correct column names from the CSVs
# corr_on  = sample_nearest(corr,    "current_height_correction")
# corr_off = sample_nearest(no_corr, "current_height_no_correction")
# ideal    = [4] * len(sample_distances)

# # ---- Plot ----
# plt.figure(figsize=(8,6))

# plt.plot(sample_distances, ideal, '--', label="Ideal Height (4 mm)")
# plt.plot(sample_distances, corr_off, '-o', label="Correction OFF")
# plt.plot(sample_distances, corr_on,  '-o', label="Correction ON")

# plt.xlabel("Distance Along Print Path (mm)")
# plt.ylabel("Measured Height (mm)")
# plt.title("Height Profile Comparison: Correction OFF vs ON")

# plt.grid(True, linestyle='--', alpha=0.4)
# plt.legend()
# plt.tight_layout()
# plt.show()
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# ASME Journal Figure Style Settings
# ---------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 12,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 11,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "lines.linewidth": 2,
    "lines.markersize": 7,
})

# ---------------------------------------------------------
# Load CSVs
# ---------------------------------------------------------
# corr = pd.read_csv('SLPC_correction_variation_5_per_s.csv')
# no_corr = pd.read_csv('SLPC_no_correction_variation_5_per_s.csv')
corr = pd.read_csv('SLP_correction_0.csv')
no_corr = pd.read_csv('SLP_no_correction_0.csv')

# Extract actual distance column
distance_values = corr['distance'].values

# Sample distances for comparison
sample_distances = [0, 200, 400, 600, 800, 1000]

# ---------------------------------------------------------
# Helper: find nearest value in dataset
# ---------------------------------------------------------
def sample_nearest(df, height_col):
    values = []
    for target in sample_distances:
        idx = (df['distance'] - target).abs().idxmin()
        values.append(df.loc[idx, height_col])
    return values

# ---------------------------------------------------------
# Correct data column names
# (Your CSV uses these exact names)
# ---------------------------------------------------------
corr_on  = sample_nearest(corr,    "current_height")
corr_off = sample_nearest(no_corr, "current_height")
ideal    = [4] * len(sample_distances)

# ---------------------------------------------------------
# Plot (ASME compliant)
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(6,4.5))  # ASME recommended size

# Ideal height
ax.plot(sample_distances, ideal, linestyle='--',
        color='black', label="Ideal Height (4 mm)")

# Correction OFF
ax.plot(sample_distances, corr_off, '-o',
        color='gray', label="Correction OFF")

# Correction ON
ax.plot(sample_distances, corr_on, '-x',
        color='black', fillstyle='none',
        label="Correction ON")

# Labels
ax.set_xlabel("Distance Along Print Path (mm)")
ax.set_ylabel("Measured Height (mm)")

# Title (ASME allows short descriptive titles)
ax.set_title("Height Profile Comparison: Correction OFF vs ON")

# Grid must be subtle
ax.grid(True, linestyle='--', linewidth=0.6, alpha=0.5)

# Legend frame off for ASME
ax.legend(frameon=False)

plt.tight_layout()
plt.show()
