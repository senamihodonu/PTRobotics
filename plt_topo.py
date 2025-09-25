import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

# === Load CSV ===
# CSV should have columns: X, Y, Height
df = pd.read_csv("samples.csv")

x = df["x"].values
y = df["y"].values
z = df["current_height"].values

# === Create grid for interpolation ===
grid_x, grid_y = np.mgrid[min(x):max(x):200j, min(y):max(y):200j]
grid_z = griddata((x, y), z, (grid_x, grid_y), method='cubic')

# === PLOTS ===
fig = plt.figure(figsize=(14, 6))

# --- 3D Surface ---
ax1 = fig.add_subplot(1, 2, 1, projection="3d")
surf = ax1.plot_surface(grid_x, grid_y, grid_z, cmap="viridis", linewidth=0, antialiased=True)
fig.colorbar(surf, ax=ax1, shrink=0.5, aspect=10, label="Height")
ax1.set_title("3D Topographical Surface")
ax1.set_xlabel("X")
ax1.set_ylabel("Y")
ax1.set_zlabel("Height")

# --- 2D Contour ---
ax2 = fig.add_subplot(1, 2, 2)
contour = ax2.contourf(grid_x, grid_y, grid_z, levels=30, cmap="viridis")
fig.colorbar(contour, ax=ax2, shrink=0.8, label="Height")
ax2.set_title("2D Topographical Contour Map")
ax2.set_xlabel("X")
ax2.set_ylabel("Y")

plt.tight_layout()
plt.show()
