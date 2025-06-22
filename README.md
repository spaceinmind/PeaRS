# Multi-Peak Pulse Analysis

This repository contains a Python script for detecting and visualizing multiple pulse components in pulsar profiles using PSRCHIVE archives. It is designed for use in fast radio burst (FRB) or pulsar studies. For more details, please refer to Ho et al. 2025, MNRAS, Section 3.4.

## Features

- Background subtraction and noise estimation
- Peak detection and multi-component fitting
- S/N thresholding
- Automatic plotting with peak annotations
- List of the peak positions and snr in .tsv

## Requirements

Install dependencies using:

```bash
pip install -r requirements.txt
```

## Usage

Put your `.ar` files in a directory, and use a `.cat` TSV catalog with a `#filename` column and `snr_xprof` values.

Run the script:

```bash
python scripts/detect_multipeak_pulses.py
```

Plots will be saved to `testplots`.

Example plot and tsv
