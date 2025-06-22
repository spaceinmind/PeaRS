#!/usr/bin/env python3
"""
PeaRS – Peak-finding and SNR for Radio Signals
A Python script for detecting and visualizing multiple pulse components in pulsar profiles using PSRCHIVE archives.  
It is designed for use in fast radio burst (FRB) or pulsar studies.  
For more details, please refer to Ho et al. 2025, MNRAS, Section 3.4.

Author: Simon C.-C. Ho
Email: simon.ho@anu.edu.au
"""

import os
import matplotlib
from matplotlib.ticker import FormatStrFormatter
matplotlib.use('TkAgg')  # Use TkAgg backend for interactive plots
import psrchive
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Configure plot font
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 32

# Read and save
catname = 'catalog/multi_git.cat'
savename = 'results.tsv/pulse_top4_summary.tsv'

# --- Utility functions ---

def subtract_background(pulse, bkg_start, bkg_end):
    """Subtracts the mean background level from the pulse data."""
    bkg_data = pulse[bkg_start:bkg_end]
    bkg_level = np.mean(bkg_data)
    return pulse - bkg_level

def measure_noise(pulse, bkg_start, bkg_end):
    """Measures the noise level (standard deviation) in a background region."""
    bkg_data = pulse[bkg_start:bkg_end]
    noise = np.std(bkg_data)
    return noise

def find_pulses(pulse, num_pulses=10, min_separation=2, max_separation=200, merge_threshold=0.2):
    """Identifies multiple pulses in a 1D pulse profile."""
    pulse_indices = np.argpartition(pulse, -num_pulses)[-num_pulses:]
    pulse_indices = pulse_indices[np.argsort(pulse[pulse_indices])[::-1]]
    pulses = []
    for idx in pulse_indices:
        half_max_level = (np.max(pulse) + np.min(pulse)) / 2
        pulse_start_indices = np.where(pulse[:idx] < half_max_level)[0]
        pulse_start = pulse_start_indices[-1] if len(pulse_start_indices) > 0 else 0
        pulse_end_indices = np.where(pulse[idx:] < half_max_level)[0]
        pulse_end = pulse_end_indices[0] + idx + 1 if len(pulse_end_indices) > 0 else len(pulse)
        pulse_width = pulse_end - pulse_start
        pulse_center = pulse_start + pulse_width / 2
        noise = measure_noise(pulse, 0, 1024)
        if pulse[idx] > pulse[pulse_start] + 3 * noise and pulse[idx] > pulse[pulse_end - 1] + 3 * noise:
            if pulses and abs(pulse_center - pulses[-1][0]) < merge_threshold * (pulse_width + pulses[-1][1]):
                new_pulse_center = (pulse_center + pulses[-1][0]) / 2
                new_pulse_width = pulse_end - pulses[-1][0]
                new_pulse_height = max(pulse[idx], pulses[-1][2])
                pulses[-1] = (new_pulse_center, new_pulse_width, new_pulse_height)
            else:
                if all(min_separation < abs(pulse_center - p[0]) < max_separation for p in pulses):
                    pulses.append((pulse_center, pulse_width, pulse[idx]))
    return pulses

def calculate_snr(pulse, pulse_center, pulse_width):
    """Calculates the signal-to-noise ratio for a pulse region."""
    pulse_segment = pulse[int(pulse_center - pulse_width / 2):int(pulse_center + pulse_width / 2)]
    pulse_flux = np.sum(pulse_segment)
    bkg_start = int(pulse_center) - 500
    bkg_end = int(pulse_center) - 400
    noise = measure_noise(pulse, bkg_start, bkg_end)
    noise *= np.sqrt(pulse_width)
    snr = pulse_flux / noise
    return snr

# --- Load catalog and setup ---
df = pd.read_csv('~/python/multi_git.cat', delimiter='\t')
df_snr10 = df[df['snr_xprof'] > 10]
file_list = df_snr10['#filename'].apply(os.path.expanduser).tolist()

output_dir = 'plots'
os.makedirs(output_dir, exist_ok=True)

# Create a list to store pulse measurements for output
results = []

# --- Batch processing setup ---
batch_size = 5
num_batches = (len(file_list) + batch_size - 1) // batch_size

for batch_idx in range(num_batches):
    batch_files = file_list[batch_idx * batch_size:(batch_idx + 1) * batch_size]
    fig, axes = plt.subplots(len(batch_files), 1, figsize=(10, 3 * len(batch_files)), sharex=True)
    fig.text(0.04, 0.5, 'Flux Density (Jy)', va='center', rotation='vertical')

    if len(batch_files) == 1:
        axes = [axes]

    for idx, (ax, filename) in enumerate(zip(axes, batch_files)):
        try:
            ar = psrchive.Archive_load(filename)
            ar.dedisperse()
            ar.remove_baseline()
            data = ar.get_data()
            Nphase = ar.get_nbin()
            mask = ar.get_weights()
            for i in range(len(mask[0, :])):
                data[0, 0, i, :] *= mask[0, i]
            time_phase_freq = np.mean(data, axis=1)
            time_phase = np.mean(time_phase_freq, axis=1)
            pulse = np.mean(time_phase, axis=0)
            pulse = subtract_background(pulse, 0, 1024)

            # --- Pulse detection and analysis ---
            pulses = find_pulses(pulse)

            if len(pulses) > 0:
                top_pulses_info = []
                for pulse_center, pulse_width, _ in pulses[:4]:  # Take top 4
                    snr = calculate_snr(pulse, pulse_center, pulse_width)
                    phase_pos = pulse_center / Nphase  # Convert to phase [0, 1]
                    top_pulses_info.append((snr, phase_pos))

                # Pad missing pulses with NaN
                while len(top_pulses_info) < 4:
                    top_pulses_info.append((np.nan, np.nan))

                # Store result
                results.append({
                    'filename': filename,
                    'snr_1': top_pulses_info[0][0],
                    'phase_1': top_pulses_info[0][1],
                    'snr_2': top_pulses_info[1][0],
                    'phase_2': top_pulses_info[1][1],
                    'snr_3': top_pulses_info[2][0],
                    'phase_3': top_pulses_info[2][1],
                    'snr_4': top_pulses_info[3][0],
                    'phase_4': top_pulses_info[3][1],
                })

                # Optional plot if SNR criteria are met
                if top_pulses_info[0][0] > 10 and top_pulses_info[1][0] > 10:
                    phase = np.linspace(0, 1, len(pulse))
                    ax.plot(phase - 0.2, pulse, color='k', label='Pulse Profile')
                    peak_region_shown = False
                    for pulse_center, pulse_width, _ in pulses[:5]:
                        pulse_start = pulse_center - pulse_width / 2
                        pulse_end = pulse_center + pulse_width / 2
                        ax.axvspan(pulse_start / Nphase - 0.2, pulse_end / Nphase - 0.2,
                                   color='blue', alpha=0.1,
                                   label='Peak Region' if not peak_region_shown else None)
                        peak_region_shown = True
                        ax.axvline(x=pulse_center / Nphase - 0.2, color='r', linestyle='--',
                                   label=f'Peak at {pulse_center / Nphase - 0.2:.3f}')
                    ax.legend(loc='upper left', fontsize=20)

        except Exception as e:
            print(f"Error processing file {filename}: {e}")

    # Axis formatting
    axes[-1].set_xlabel('Pulse Phase')
    for ax in axes:
        ax.set_xlim(0.6, 0.8)
        ax.xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        ax.tick_params(axis='both', length=10)

    fig.tight_layout(rect=[0.04, 0.0, 1, 1])
    fig.subplots_adjust(hspace=0.05)
    batch_plot_name = f'combined_pulses_batch_{batch_idx + 1}.pdf'
    plt.savefig(os.path.join(output_dir, batch_plot_name), bbox_inches='tight', dpi=300)
    plt.show()

# --- Save results to TSV ---
results_df = pd.DataFrame(results)
results_df.to_csv(savename, sep='\t', index=False, float_format='%.3f')
print("Saved pulse summary to ",savename)

