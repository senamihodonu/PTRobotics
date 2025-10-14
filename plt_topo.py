import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from mpl_toolkits.mplot3d import Axes3D  # needed for 3D plots

# === Argument Parsing ===
parser = argparse.ArgumentParser(description="Plot 2D/3D topographical map from CSV.")
parser.add_argument("filename", type=str, help="CSV file containing x, y, current_height columns")
parser.add_argument("--compare", type=str, default=None,
                    help="Optional second CSV file for comparison")
parser.add_argument("--mode", type=str, default="both", choices=["2D", "3D", "both"],
                    help="Plot mode: 2D contour, 3D surface, or both")
parser.add_argument("--grid", type=int, default=200,
                    help="Number of points along each axis for interpolation grid (higher = finer resolution)")
parser.add_argument("--title", type=str, default=None,
                    help="Custom title for plots (overrides default titles)")
args = parser.parse_args()

# === Helper function ===
def load_and_process(filename, grid_res, hmin=0, hmax=6):
    df = pd.read_csv(filename).dropna(subset=["x", "y", "current_height"])
    x = df["x"].values
    y = df["y"].values
    z = df["current_height"].values

    grid_x, grid_y = np.mgrid[min(x):max(x):complex(grid_res),
                              min(y):max(y):complex(grid_res)]
    grid_z = griddata((x, y), z, (grid_x, grid_y), method="cubic")
    if grid_z is not None:
        grid_z = np.clip(grid_z, hmin, hmax)

    min_idx = np.nanargmin(z)
    max_idx = np.nanargmax(z)

    return {
        "x": x, "y": y, "z": z,
        "grid_x": grid_x, "grid_y": grid_y, "grid_z": grid_z,
        "x_min": x[min_idx], "y_min": y[min_idx], "z_min": z[min_idx],
        "x_max": x[max_idx], "y_max": y[max_idx], "z_max": z[max_idx],
    }

# === Constants ===
HEIGHT_MIN, HEIGHT_MAX = 0, 6

# === Load datasets ===
datasets = [load_and_process(args.filename, args.grid, HEIGHT_MIN, HEIGHT_MAX)]
titles = [args.title if args.title else "Primary Dataset"]

if args.compare:
    datasets.append(load_and_process(args.compare, args.grid, HEIGHT_MIN, HEIGHT_MAX))
    titles.append("Comparison Dataset")

# === Plotting ===
if args.mode in ["2D", "both"] and args.compare:
    # Special case: side-by-side comparison for 2D
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharex=True, sharey=True)
    contours = []

    for i, data in enumerate(datasets):
        ax2d = axes[i]
        levels = np.linspace(HEIGHT_MIN, HEIGHT_MAX, HEIGHT_MAX - HEIGHT_MIN + 1)
        contour = ax2d.contourf(
            data["grid_x"], data["grid_y"], data["grid_z"],
            levels=levels, cmap="viridis",
            vmin=HEIGHT_MIN, vmax=HEIGHT_MAX
        )
        contours.append(contour)
        ax2d.set_title(f"{titles[i]}")
        ax2d.set_xlabel("X")
        ax2d.set_ylabel("Y")
        ax2d.scatter(data["x_min"], data["y_min"], color="red", s=40,
                     label=f"Min: {data['z_min']:.2f}")
        ax2d.scatter(data["x_max"], data["y_max"], color="blue", s=40,
                     label=f"Max: {data['z_max']:.2f}")
        ax2d.legend(loc="upper right")

    # Shared colorbar in the middle
    fig.subplots_adjust(wspace=0.3)
    cbar_ax = fig.add_axes([0.47, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(contours[0], cax=cbar_ax)
    cbar.set_label("Height")

elif args.mode in ["3D", "both"] or not args.compare:
    # General case: handle 3D and single dataset
    nrows = len(datasets)
    fig = plt.figure(figsize=(14, 6 * nrows))

    for i, data in enumerate(datasets):
        # --- 3D Plot ---
        if args.mode in ["3D", "both"]:
            ax3d = fig.add_subplot(nrows, 2 if args.mode == "both" else 1,
                                   i*2+1 if args.mode=="both" else i+1, projection="3d")
            surf = ax3d.plot_surface(data["grid_x"], data["grid_y"], data["grid_z"],
                                     cmap="viridis", linewidth=0, antialiased=True,
                                     vmin=HEIGHT_MIN, vmax=HEIGHT_MAX)
            fig.colorbar(surf, ax=ax3d, shrink=0.5, aspect=10, label="Height")
            ax3d.set_title(f"{titles[i]} - 3D Surface")
            ax3d.set_xlabel("X")
            ax3d.set_ylabel("Y")
            ax3d.set_zlabel("Height")
            ax3d.set_zlim(HEIGHT_MIN, HEIGHT_MAX)
            ax3d.scatter(data["x_min"], data["y_min"], data["z_min"], color="red", s=50)
            ax3d.scatter(data["x_max"], data["y_max"], data["z_max"], color="blue", s=50)

        # --- 2D Plot ---
        if args.mode in ["2D", "both"]:
            ax2d = fig.add_subplot(nrows, 2 if args.mode == "both" else 1,
                                   i*2+2 if args.mode=="both" else i+1)
            levels = np.linspace(HEIGHT_MIN, HEIGHT_MAX, HEIGHT_MAX - HEIGHT_MIN + 1)
            contour = ax2d.contourf(
                data["grid_x"], data["grid_y"], data["grid_z"],
                levels=levels, cmap="viridis",
                vmin=HEIGHT_MIN, vmax=HEIGHT_MAX
            )
            plt.colorbar(contour, ax=ax2d, shrink=0.8, label="Nozzle height above print surface")
            ax2d.set_title(f"{titles[i]}")
            ax2d.set_xlabel("X position")
            ax2d.set_ylabel("Y position")
            ax2d.scatter(data["x_min"], data["y_min"], color="red", s=40)
            ax2d.scatter(data["x_max"], data["y_max"], color="blue", s=40)

plt.tight_layout()
plt.show()
