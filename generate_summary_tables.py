#!/usr/bin/env python3
"""
Generate summary tables from existing per-event completeness and purity tables.
This aggregates all per-event data into summary tables.
"""

import pandas as pd
from pathlib import Path
import numpy as np

def generate_summary_tables():
    output_base = Path("/exp/sbnd/data/users/prabhjot/wirecell_clustering/cluster_evaluation/multi_file_plots_without_deghosting/2view/2view/apa_APA0")

    # Find all per-event completeness tables
    eff_tables = list(output_base.glob("*/event_*/completeness/CompletenessTable.txt"))
    pur_tables = list(output_base.glob("*/event_*/purity/PurityTable.txt"))

    print(f"Found {len(eff_tables)} completeness tables")
    print(f"Found {len(pur_tables)} purity tables")

    # Read and combine completeness tables
    eff_data = []
    for table_file in eff_tables:
        try:
            # Skip the header lines (=====...) and find the data
            with open(table_file, 'r') as f:
                lines = f.readlines()

            # Find the line with column headers
            header_idx = -1
            for i, line in enumerate(lines):
                if 'Event' in line and 'True ID' in line:
                    header_idx = i
                    break

            if header_idx >= 0:
                # Skip until after the dashes line
                data_start = header_idx + 2  # header + dashes
                # Find where data ends (next dashes or ====)
                data_end = len(lines)
                for i in range(data_start, len(lines)):
                    if lines[i].strip().startswith('-') or lines[i].strip().startswith('='):
                        data_end = i
                        break

                # Read the data
                if data_end > data_start:
                    data_lines = ''.join(lines[data_start:data_end])
                    from io import StringIO
                    df = pd.read_csv(StringIO(data_lines), sep='\s+', skipinitialspace=True)
                    eff_data.append(df)
        except Exception as e:
            print(f"  Error reading {table_file.name}: {e}")
            pass

    if eff_data:
        eff_all = pd.concat(eff_data, ignore_index=True)
        print(f"Total completeness data: {len(eff_all)} rows")

        # Generate summary completeness table
        output_text = "\n" + "="*120 + "\n"
        output_text += "SUMMARY COMPLETENESS TABLE - ALL FILES AND ALL EVENTS\n"
        output_text += "Sorted by True Cluster Energy (descending)\n"
        output_text += "="*120 + "\n\n"

        output_text += f"{'Event':<8} {'True ID':<12} {'Reco ID':<12} {'True Energy':<15} {'Matched Energy':<18} {'Completeness':<12} {'Status':<20}\n"
        output_text += "-"*120 + "\n"

        for _, row in eff_all.iterrows():
            output_text += f"{str(row.get('Event', '')):<8} {str(row.get('True ID', '')):<12} {str(row.get('Reco ID', '')):<12} {str(row.get('True Energy', '')):<15} {str(row.get('Matched Energy', '')):<18} {str(row.get('Completeness', '')):<12} {str(row.get('Status', '')):<20}\n"

        output_text += "-"*120 + "\n\n"
        output_text += f"Total pairs: {len(eff_all)}\n"

        eff_file = output_base / "SUMMARY_CompletenessTable.txt"
        with open(eff_file, 'w') as f:
            f.write(output_text)
        print(f"✓ Created {eff_file.name}")

    # Read and combine purity tables
    pur_data = []
    for table_file in pur_tables:
        try:
            # Skip the header lines (=====...) and find the data
            with open(table_file, 'r') as f:
                lines = f.readlines()

            # Find the line with column headers
            header_idx = -1
            for i, line in enumerate(lines):
                if 'Event' in line and 'Reco ID' in line:
                    header_idx = i
                    break

            if header_idx >= 0:
                # Skip until after the dashes line
                data_start = header_idx + 2  # header + dashes
                # Find where data ends (next dashes or ====)
                data_end = len(lines)
                for i in range(data_start, len(lines)):
                    if lines[i].strip().startswith('-') or lines[i].strip().startswith('='):
                        data_end = i
                        break

                # Read the data
                if data_end > data_start:
                    data_lines = ''.join(lines[data_start:data_end])
                    from io import StringIO
                    df = pd.read_csv(StringIO(data_lines), sep='\s+', skipinitialspace=True)
                    pur_data.append(df)
        except Exception as e:
            print(f"  Error reading {table_file.name}: {e}")
            pass

    if pur_data:
        pur_all = pd.concat(pur_data, ignore_index=True)
        print(f"Total purity data: {len(pur_all)} rows")

        # Generate summary purity table
        output_text = "\n" + "="*140 + "\n"
        output_text += "SUMMARY PURITY TABLE - ALL FILES AND ALL EVENTS\n"
        output_text += "Sorted by Reco Cluster Charge (descending)\n"
        output_text += "="*140 + "\n\n"

        output_text += f"{'Event':<8} {'Reco ID':<12} {'True ID':<12} {'Reco Charge':<15} {'Matched Pts':<15} {'Total Pts':<12} {'Purity':<12} {'Status':<20}\n"
        output_text += "-"*140 + "\n"

        for _, row in pur_all.iterrows():
            output_text += f"{str(row.get('Event', '')):<8} {str(row.get('Reco ID', '')):<12} {str(row.get('True ID', '')):<12} {str(row.get('Reco Charge', '')):<15} {str(row.get('Matched Pts', '')):<15} {str(row.get('Total Pts', '')):<12} {str(row.get('Purity', '')):<12} {str(row.get('Status', '')):<20}\n"

        output_text += "-"*140 + "\n\n"
        output_text += f"Total pairs: {len(pur_all)}\n"

        pur_file = output_base / "SUMMARY_PurityTable.txt"
        with open(pur_file, 'w') as f:
            f.write(output_text)
        print(f"✓ Created {pur_file.name}")

if __name__ == '__main__':
    generate_summary_tables()
