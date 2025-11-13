import pandas as pd
import matplotlib.pyplot as plt

# Data
correction = pd.read_csv('single_layer_print_bed_correction.csv')
no_correction = pd.read_csv('single_layer_print_bed_no_correction_1 copy.csv')

print(correction.head())
print(no_correction.head())