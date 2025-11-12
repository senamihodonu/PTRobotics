import pandas as pd
import matplotlib.pyplot as plt

# Data
distance = [0, 200, 400, 600, 800, 1000]
ideal = [4, 4, 4, 4, 4, 4]
off =   [4.0, 5.2, 6.5, 7.0, 5.8, 4.3]   # Correction OFF
on =    [4.1, 4.3, 4.4, 4.6, 4.2, 4.1]   # Correction ON

df = pd.DataFrame({
    "Distance (mm)": distance,
    "Ideal Height (mm)": ideal,
    "Correction OFF (mm)": off,
    "Correction ON (mm)": on
})

# Plot
plt.figure(figsize=(10,4))
plt.plot(df["Distance (mm)"], df["Ideal Height (mm)"], linestyle="--", label="Ideal Height (4 mm)")
plt.plot(df["Distance (mm)"], df["Correction OFF (mm)"], marker="o", label="Correction OFF")
plt.plot(df["Distance (mm)"], df["Correction ON (mm)"], marker="o", label="Correction ON")

plt.xlabel("Distance Along Print Path (mm)")
plt.ylabel("Measured Height (mm)")
plt.title("Height Profile Comparison: Correction OFF vs ON")
plt.legend()
plt.tight_layout()
plt.show()
# # import matplotlib.pyplot as plt

# # # Data
# # distance = [0, 200, 400, 600, 800, 1000]
# # ideal = [4, 4, 4, 4, 4, 4]
# # off =   [4.0, 5.2, 6.5, 7.0, 5.8, 4.3]   # Correction OFF
# # on  =   [4.1, 4.3, 4.4, 4.6, 4.2, 4.1]   # Correction ON

# # # Begin plot
# # fig, ax = plt.subplots(figsize=(7, 3.5))

# # # Plot lines
# # ax.plot(distance, ideal, linestyle='--', linewidth=1.5, label='Ideal Height (4 mm)')
# # ax.plot(distance, off, marker='o', linewidth=1.8, label='Correction OFF')
# # ax.plot(distance, on, marker='o', linewidth=1.8, label='Correction ON')

# # # Labels and styling
# # ax.set_xlabel("Distance Along Print Path (mm)", fontsize=11)
# # ax.set_ylabel("Measured Height (mm)", fontsize=11)
# # ax.set_title("Height Profile Comparison: Correction OFF vs ON", fontsize=12)

# # # Legend
# # ax.legend(fontsize=10, frameon=False)

# # # Tight layout for publication
# # plt.tight_layout()
# # plt.show()
# # import matplotlib.pyplot as plt
# # from matplotlib import rcParams

# # # ASME Figure Formatting
# # rcParams['font.family'] = 'serif'
# # rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif', 'STIXGeneral']
# # rcParams['mathtext.fontset'] = 'stix'
# # rcParams['font.size'] = 10
# # rcParams['axes.linewidth'] = 0.75
# # rcParams['xtick.direction'] = 'in'
# # rcParams['ytick.direction'] = 'in'

# # # Data
# # distance = [0, 200, 400, 600, 800, 1000]
# # ideal = [4, 4, 4, 4, 4, 4]
# # off =   [4.0, 5.2, 6.5, 7.0, 5.8, 4.3]   # Correction OFF
# # on  =   [4.1, 4.3, 4.4, 4.6, 4.2, 4.1]   # Correction ON

# # # Create figure (single-column ASME width ~3.5" → convert to inches)
# # fig, ax = plt.subplots(figsize=(3.5, 2.2))

# # # Plot
# # ax.plot(distance, ideal, linestyle='--', linewidth=1.0, label='Ideal Height (4 mm)')
# # ax.plot(distance, off, marker='o', markersize=4, linewidth=1.1, label='Correction OFF')
# # ax.plot(distance, on, marker='o', markersize=4, linewidth=1.1, label='Correction ON')

# # # Axes labels
# # ax.set_xlabel("Distance Along Print Path (mm)", labelpad=4)
# # ax.set_ylabel("Measured Height (mm)", labelpad=4)

# # # No title in ASME figures — captions go underneath in the paper
# # # ax.set_title("Height Profile Comparison")  # <- intentionally removed

# # # Legend (ASME: no frame box)
# # ax.legend(frameon=False, fontsize=9, handlelength=2.4, borderpad=0.3)

# # # Tight layout for LaTeX/Overleaf figure inclusion
# # plt.tight_layout()

# # # Display
# # plt.show()

# import matplotlib.pyplot as plt
# from matplotlib import rcParams

# # IEEE Figure Formatting
# rcParams['font.family'] = 'serif'  # IEEE allows serif or sans; serif prints cleaner
# rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif', 'STIXGeneral']
# rcParams['mathtext.fontset'] = 'stix'
# rcParams['font.size'] = 10
# rcParams['axes.linewidth'] = 0.8
# rcParams['xtick.direction'] = 'in'
# rcParams['ytick.direction'] = 'in'
# rcParams['xtick.major.size'] = 4
# rcParams['ytick.major.size'] = 4

# # Data
# distance = [0, 200, 400, 600, 800, 1000]
# ideal = [4, 4, 4, 4, 4, 4]
# off =   [4.0, 5.2, 6.5, 7.0, 5.8, 4.3]   # Correction OFF
# on  =   [4.1, 4.3, 4.4, 4.6, 4.2, 4.1]   # Correction ON

# # IEEE single-column figure width typically ~3.4 in
# fig, ax = plt.subplots(figsize=(3.4, 2.3))

# # Plot
# ax.plot(distance, ideal, linestyle='--', linewidth=1.0, label='Ideal Height (4 mm)')
# ax.plot(distance, off, marker='o', markersize=4, linewidth=1.2, label='Correction OFF')
# ax.plot(distance, on, marker='o', markersize=4, linewidth=1.2, label='Correction ON')

# # Labels (no title inside IEEE figures — caption will explain in paper)
# ax.set_xlabel("Distance Along Print Path (mm)", labelpad=3)
# ax.set_ylabel("Measured Height (mm)", labelpad=3)

# # Legend (IEEE style: no frame box)
# ax.legend(frameon=False, fontsize=9, handlelength=2.2)

# # No grid (IEEE figures avoid clutter unless essential)
# # ax.grid(True, linestyle=':', linewidth=0.5, alpha=0.6)  # <- Optional

# plt.tight_layout()
# plt.show()

