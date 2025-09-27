import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

# === Argument Parsing ===
parser = argparse.ArgumentParser(description="Plot 2D/3D topographical map from CSV.")
parser.add_argument("filename", type=str, help="CSV file containing x, y, current_height columns")
parser.add_argument("--mode", type=str, default="both", choices=["2D", "3D", "both"],
                    help="Plot mode: 2D contour, 3D surface, or both")
parser.add_argument("--grid", type=int, default=200,
                    help="Number of points along each axis for interpolation grid (higher = finer resolution)")
parser.add_argument("--title", type=str, default=None,
                    help="Custom title for plots (overrides default titles)")
args = parser.parse_args()

# === Load CSV ===
df = pd.read_csv(args.filename)
df = df.dropna(subset=["x", "y", "current_height"])

x = df["x"].values
y = df["y"].values
z = df["current_height"].values

# === Create grid for interpolation ===
grid_x, grid_y = np.mgrid[min(x):max(x):complex(args.grid),
                          min(y):max(y):complex(args.grid)]
grid_z = griddata((x, y), z, (grid_x, grid_y), method="cubic")

# === Clip to measured range ===
zmin, zmax = np.nanmin(z), np.nanmax(z)
if grid_z is not None:
    grid_z = np.clip(grid_z, zmin, zmax)

# Find min/max points from raw data
min_idx = np.nanargmin(z)
max_idx = np.nanargmax(z)
x_min, y_min, z_min = x[min_idx], y[min_idx], z[min_idx]
x_max, y_max, z_max = x[max_idx], y[max_idx], z[max_idx]

# === Plotting ===
if args.mode in ("3D", "both"):
    fig = plt.figure(figsize=(14, 6))
    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    surf = ax1.plot_surface(grid_x, grid_y, grid_z, cmap="viridis",
                            linewidth=0, antialiased=True, vmin=zmin, vmax=zmax)
    fig.colorbar(surf, ax=ax1, shrink=0.5, aspect=10, label="Height")
    ax1.set_title(args.title if args.title else "3D Topographical Surface")
    ax1.set_xlabel("X")
    ax1.set_ylabel("Y")
    ax1.set_zlabel("Height")
    ax1.set_zlim(zmin, zmax)
    ax1.scatter(x_min, y_min, z_min, color="red", s=50, label=f"Min: {z_min:.2f}")
    ax1.scatter(x_max, y_max, z_max, color="blue", s=50, label=f"Max: {z_max:.2f}")
    ax1.legend(loc="upper right")

if args.mode in ("2D", "both"):
    if args.mode == "2D":
        plt.figure(figsize=(8, 6))
        ax2 = plt.gca()
    else:
        ax2 = fig.add_subplot(1, 2, 2)
    contour = ax2.contourf(grid_x, grid_y, grid_z, levels=30, cmap="viridis", vmin=zmin, vmax=zmax)
    plt.colorbar(contour, ax=ax2, shrink=0.8, label="Height")
    ax2.set_title(args.title if args.title else "2D Topographical Contour Map")
    ax2.set_xlabel("X")
    ax2.set_ylabel("Y")
    ax2.scatter(x_min, y_min, color="red", s=40, label=f"Min: {z_min:.2f}")
    ax2.scatter(x_max, y_max, color="blue", s=40, label=f"Max: {z_max:.2f}")
    ax2.legend(loc="upper right")

plt.tight_layout()
plt.show()

# === Debug check ===
print("Raw data range:", zmin, zmax)
print("Clipped grid range:", np.nanmin(grid_z), np.nanmax(grid_z))
print(f"Grid resolution: {args.grid}x{args.grid}")
