import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

# === Load CSV ===
df = pd.read_csv("z_correction1.csv")

# Drop rows with NaN in x, y, or current_height
df = df.dropna(subset=["x", "y", "current_height"])

x = df["x"].values
y = df["y"].values
z = df["current_height"].values

# === Create grid for interpolation ===
grid_x, grid_y = np.mgrid[min(x):max(x):200j, min(y):max(y):200j]
grid_z = griddata((x, y), z, (grid_x, grid_y), method="cubic")

# === Define z range from raw data ===
zmin, zmax = np.nanmin(z), np.nanmax(z)
z_range = (zmin - 2, zmax + 2)

# --- Clip interpolation to measured range ---
if grid_z is not None:
    grid_z = np.clip(grid_z, zmin, zmax)

# Find coordinates of min and max (from raw data)
min_idx = np.nanargmin(z)
max_idx = np.nanargmax(z)
x_min, y_min, z_min = x[min_idx], y[min_idx], z[min_idx]
x_max, y_max, z_max = x[max_idx], y[max_idx], z[max_idx]

# === PLOTS ===
fig = plt.figure(figsize=(14, 6))

# --- 3D Surface ---
ax1 = fig.add_subplot(1, 2, 1, projection="3d")
surf = ax1.plot_surface(grid_x, grid_y, grid_z, cmap="viridis",
                        linewidth=0, antialiased=True,
                        vmin=z_range[0], vmax=z_range[1])
fig.colorbar(surf, ax=ax1, shrink=0.5, aspect=10, label="Height")
ax1.set_title("3D Topographical Surface")
ax1.set_xlabel("X")
ax1.set_ylabel("Y")
ax1.set_zlabel("Height")
ax1.set_zlim(*z_range)

# Mark min and max points
ax1.scatter(x_min, y_min, z_min, color="red", s=50, label=f"Min: {z_min:.2f}")
ax1.scatter(x_max, y_max, z_max, color="blue", s=50, label=f"Max: {z_max:.2f}")
ax1.legend(loc="upper right")

# --- 2D Contour ---
ax2 = fig.add_subplot(1, 2, 2)
contour = ax2.contourf(grid_x, grid_y, grid_z, levels=30,
                       cmap="viridis", vmin=z_range[0], vmax=z_range[1])
fig.colorbar(contour, ax=ax2, shrink=0.8, label="Height")
ax2.set_title("2D Topographical Contour Map")
ax2.set_xlabel("X")
ax2.set_ylabel("Y")

# Mark min and max points
ax2.scatter(x_min, y_min, color="red", s=40, label=f"Min: {z_min:.2f}")
ax2.scatter(x_max, y_max, color="blue", s=40, label=f"Max: {z_max:.2f}")
ax2.legend(loc="upper right")

plt.tight_layout()
plt.show()

# === Debug check ===
print("Raw data range:", zmin, zmax)
print("Clipped grid range:", np.nanmin(grid_z), np.nanmax(grid_z))
