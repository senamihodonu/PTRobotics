import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline

# ---------------------------------------------------------
# Plot Modes (choose one)
# ---------------------------------------------------------
USE_SMOOTH_LINES = True    # Smooth spline curves (except ideal, which is always smooth)
USE_SCATTER_ONLY = False    # Scatter plot only (experimental data only)

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
# Load CSV Data
# ---------------------------------------------------------
corr          = pd.read_csv('SLPC_correction_8_per_s_0_tol.csv')   # Correction ON
corr_w_tol    = pd.read_csv('SLP_correction_0.csv')                # Correction ON (tolerance)
no_corr       = pd.read_csv('SLP_no_correction_0.csv')             # Correction OFF

sample_distances = [0, 100, 200, 300, 400, 500,
                    600, 700, 800, 900, 1000]

# ---------------------------------------------------------
# Helper Function: Nearest-value sampling
# ---------------------------------------------------------
def sample_nearest(df, height_col="current_height"):
    sampled = []
    for target in sample_distances:
        idx = (df['distance'] - target).abs().idxmin()
        sampled.append(df.loc[idx, height_col])
    return sampled

# ---------------------------------------------------------
# Sample profiles
# ---------------------------------------------------------
corr_on_sample  = sample_nearest(corr)
corr_tol_sample = sample_nearest(corr_w_tol)
corr_off_sample = sample_nearest(no_corr)
ideal_height    = [4] * len(sample_distances)

# ---------------------------------------------------------
# Helper: smoothing functions
# ---------------------------------------------------------
def smooth_curve(x, y, pts=300):
    """Always used for ideal curve."""
    x_smooth = np.linspace(min(x), max(x), pts)
    spline   = make_interp_spline(x, y, k=3)
    y_smooth = spline(x_smooth)
    return x_smooth, y_smooth

def maybe_smooth(x, y, pts=300):
    """Used for experimental curves only."""
    if USE_SCATTER_ONLY:
        return x, y
    if not USE_SMOOTH_LINES:
        return x, y
    return smooth_curve(x, y, pts)

# Prepare smoothed or raw experimental data
x_off, y_off = maybe_smooth(sample_distances, corr_off_sample)
x_tol, y_tol = maybe_smooth(sample_distances, corr_tol_sample)
x_on,  y_on  = maybe_smooth(sample_distances, corr_on_sample)

# Ideal curve ALWAYS smooth
x_i, y_i = smooth_curve(sample_distances, ideal_height)

# ---------------------------------------------------------
# Plot (ASME-Compliant)
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(6, 4.5))

# ==== Ideal Reference Curve (ALWAYS SMOOTH) ====
ax.plot(
    x_i, y_i,
    linestyle='--', linewidth=1.7,
    color='dimgray',
    label="Ideal Height (4 mm)"
)

# ---------------------------------------------------------
# Experimental Curves
# ---------------------------------------------------------
if USE_SCATTER_ONLY:

    # Scatter-only mode (ideal curve still smooth line)


    ax.scatter(sample_distances, corr_tol_sample,
               color='black', marker='^',
               label="Correction ON (tolerance)")

    ax.scatter(sample_distances, corr_on_sample,
               color='darkgray', marker='x',
               label="Correction ON")
    
    ax.scatter(sample_distances, corr_off_sample,
               color='gray', marker='v',
               label="Correction OFF")

else:
    # Line / Smooth-Line mode
    ax.plot(x_off, y_off,
            linestyle='-', 
            marker=None if USE_SMOOTH_LINES else 'v',
            color='gray',
            label="Correction OFF")

    ax.plot(x_tol, y_tol,
            linestyle='-.',
            marker=None if USE_SMOOTH_LINES else 'x',
            color='black', fillstyle='none',
            label="Correction ON (tolerance)")

    ax.plot(x_on, y_on,
            linestyle=':',
            marker=None if USE_SMOOTH_LINES else 'x',
            color='darkgray',
            label="Correction ON")

# ---------------------------------------------------------
# Formatting: labels, grid, legend
# ---------------------------------------------------------
ax.set_xlabel("Distance Along Print Path (mm)")
ax.set_ylabel("Measured Height (mm)")
ax.set_title("Measured Height Profile With and Without Z-Height Correction")

ax.grid(True, linestyle='--', linewidth=0.6, alpha=0.5)
ax.legend(frameon=False)

plt.tight_layout()
plt.show()
