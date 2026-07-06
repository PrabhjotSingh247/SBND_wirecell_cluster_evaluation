import numpy as np
import pandas as pd
from pathlib import Path

def PrintEfficiencyTable(all_efficiency_results, input_directories_map, output_dir):
    """
    Print and save detailed efficiency tables sorted by true cluster energy.
    Saves organized in hierarchy: output_dir/input_file/event_N/efficiency/
    """
    
    if len(all_efficiency_results) == 0:
        print("No efficiency results to print")
        return
    
    # Group results by event
    results_by_event = {}
    for result in all_efficiency_results:
        event_key = result['event']
        # Use composite key directly as grouping key
        if event_key not in results_by_event:
            results_by_event[event_key] = []
        results_by_event[event_key].append(result)
    
    output_dir = Path(output_dir)
    
    for event_key, event_results in results_by_event.items():
        # Extract event number from composite key for formatting
        if isinstance(event_key, str) and '_' in event_key:
            event = int(event_key.rsplit('_', 1)[1])
        else:
            event = int(event_key)
        
        if event_key not in input_directories_map:
            print(f"Warning: No input directory found for event_key {event_key}")
            continue
        
        input_dir, evt_num = input_directories_map[event_key]
        input_file_name = input_dir.parent.name
        
        # Create hierarchical directory: output_dir/input_file/event_N/efficiency/
        event_output_dir = output_dir / input_file_name / f"event_{event:03d}" / "efficiency"
        event_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert to DataFrame and sort
        df = pd.DataFrame(event_results)
        df = df.sort_values('total_true_cluster_energy', ascending=False)
        
        # Prepare output text
        output_text = "\n" + "="*120 + "\n"
        output_text += f"EFFICIENCY TABLE - Event {event} ({input_file_name})\n"
        output_text += "Sorted by True Cluster Energy (descending)\n"
        output_text += "="*120 + "\n\n"
        
        # Column headers
        output_text += f"{'Event':<8} {'True ID':<12} {'Reco ID':<12} {'True Energy':<15} {'Matched Energy':<15} {'Efficiency':<12} {'Status':<20}\n"
        output_text += "-"*120 + "\n"
        
        zero_eff_count = 0
        low_eff_count = 0
        good_eff_count = 0
        
        for idx, row in df.iterrows():
            true_id = row['true_cluster_id']
            reco_id = row['reco_cluster_id']
            true_energy = row['total_true_cluster_energy']
            matched_energy = row['matched_true_cluster_energy']
            efficiency = row['efficiency_energy_weighted']
            
            if abs(efficiency - (-0.1)) < 0.001:  # Unmatched (sentinel value)
                status = "UNMATCHED"
                zero_eff_count += 1
            elif efficiency == 0:
                status = "ZERO EFFICIENCY"
                zero_eff_count += 1
            elif efficiency < 0.5:
                status = "LOW EFF (<0.5)"
                low_eff_count += 1
            else:
                status = "Good"
                good_eff_count += 1
            
            output_text += f"{event:<8} {true_id:<12.2f} {reco_id:<12.2f} {true_energy:<15.2f} {matched_energy:<15.2f} {efficiency:<12.4f} {status:<20}\n"
        
        output_text += "-"*120 + "\n\n"
        
        # Summary counts
        output_text += "SUMMARY:\n"
        output_text += f"  Total pairs: {len(df)}\n"
        output_text += f"  Zero efficiency: {zero_eff_count}\n"
        output_text += f"  Low efficiency (<0.5): {low_eff_count}\n"
        output_text += f"  Good efficiency (≥0.5): {good_eff_count}\n"
        output_text += "\n" + "="*120 + "\n"
        
        # Print to console
        print(output_text)
        
        # Save to file
        table_file = event_output_dir / "EfficiencyTable.txt"
        with open(table_file, 'w') as f:
            f.write(output_text)
        
        print(f"Saved: {table_file}\n")


def PrintEfficiencySummaryTable(all_efficiency_results, output_dir):
    """
    Print and save SUMMARY efficiency table aggregating across ALL files and ALL events.
    Saves to top-level output_dir (not nested in file/event subdirectories).
    """
    
    if len(all_efficiency_results) == 0:
        print("No efficiency results for summary table")
        return
    
    output_dir = Path(output_dir)
    
    # Convert to DataFrame and sort
    df = pd.DataFrame(all_efficiency_results)
    df = df.sort_values('total_true_cluster_energy', ascending=False)
    
    # Prepare output text
    output_text = "\n" + "="*130 + "\n"
    output_text += "SUMMARY EFFICIENCY TABLE - ALL FILES AND ALL EVENTS\n"
    output_text += "Sorted by True Cluster Energy (descending)\n"
    output_text += "="*130 + "\n\n"
    
    # Column headers
    output_text += f"{'Event':<8} {'File':<30} {'True ID':<12} {'Reco ID':<12} {'True Energy':<15} {'Matched Energy':<15} {'Efficiency':<12} {'Status':<20}\n"
    output_text += "-"*130 + "\n"
    
    zero_eff_count = 0
    low_eff_count = 0
    good_eff_count = 0
    
    for idx, row in df.iterrows():
        # Extract numeric event ID from string identifier if needed
        event_str = str(row['event'])
        event = int(event_str.split('_')[-1]) if '_' in event_str else int(event_str)
        true_id = row['true_cluster_id']
        reco_id = row['reco_cluster_id']
        true_energy = row['total_true_cluster_energy']
        matched_energy = row['matched_true_cluster_energy']
        efficiency = row['efficiency_energy_weighted']
        
        # Try to extract file name from context
        file_name = "unknown"
        
        if efficiency == 0:
            status = "ZERO EFFICIENCY"
            zero_eff_count += 1
        elif efficiency < 0.5:
            status = "LOW EFF (<0.5)"
            low_eff_count += 1
        else:
            status = "Good"
            good_eff_count += 1
        
        output_text += f"{event:<8} {file_name:<30} {true_id:<12.2f} {reco_id:<12.2f} {true_energy:<15.2f} {matched_energy:<15.2f} {efficiency:<12.4f} {status:<20}\n"
    
    output_text += "-"*130 + "\n\n"
    
    # Summary statistics
    output_text += "SUMMARY STATISTICS:\n"
    output_text += f"  Total pairs: {len(df)}\n"
    output_text += f"  Zero efficiency: {zero_eff_count}\n"
    output_text += f"  Low efficiency (<0.5): {low_eff_count}\n"
    output_text += f"  Good efficiency (≥0.5): {good_eff_count}\n"
    
    efficiencies = df['efficiency_energy_weighted'].values
    output_text += f"\n[EFFICIENCY STATISTICS]\n"
    output_text += f"  Mean:                {np.mean(efficiencies):.4f}\n"
    output_text += f"  Std Dev:             {np.std(efficiencies):.4f}\n"
    output_text += f"  Median:              {np.median(efficiencies):.4f}\n"
    output_text += f"  Min:                 {np.min(efficiencies):.4f}\n"
    output_text += f"  Max:                 {np.max(efficiencies):.4f}\n"
    output_text += f"  25th Percentile:     {np.percentile(efficiencies, 25):.4f}\n"
    output_text += f"  75th Percentile:     {np.percentile(efficiencies, 75):.4f}\n"
    
    output_text += "\n" + "="*130 + "\n"
    
    # Print to console
    print(output_text)
    
    # Save to file
    table_file = output_dir / "SUMMARY_EfficiencyTable.txt"
    with open(table_file, 'w') as f:
        f.write(output_text)
    
    print(f"Saved: {table_file}\n")



def PrintPurityTable(all_purity_results, input_directories_map, output_dir):
    """
    Print and save detailed purity tables sorted by reco cluster charge.
    Saves organized in hierarchy: output_dir/input_file/event_N/purity/
    """
    
    if len(all_purity_results) == 0:
        print("No purity results to print")
        return
    
    # Group results by event
    results_by_event = {}
    for result in all_purity_results:
        event_key = result['event']
        # Use composite key for grouping
        if event_key not in results_by_event:
            results_by_event[event_key] = []
        results_by_event[event_key].append(result)
    
    output_dir = Path(output_dir)
    
    for event_key, event_results in results_by_event.items():
        # Extract event number from composite key for formatting
        if isinstance(event_key, str) and '_' in event_key:
            event = int(event_key.rsplit('_', 1)[1])
        else:
            event = int(event_key)
        
        if event_key not in input_directories_map:
            print(f"Warning: No input directory found for event_key {event_key}")
            continue
        
        input_dir, evt_num = input_directories_map[event_key]
        input_file_name = input_dir.parent.name
        
        # Create hierarchical directory: output_dir/input_file/event_N/purity/
        event_output_dir = output_dir / input_file_name / f"event_{event:03d}" / "purity"
        event_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert to DataFrame and sort
        df = pd.DataFrame(event_results)
        df = df.sort_values('total_reco_cluster_charge', ascending=False)
        
        # Prepare output text
        output_text = "\n" + "="*130 + "\n"
        output_text += f"PURITY TABLE - Event {event} ({input_file_name})\n"
        output_text += "Sorted by Reco Cluster Charge (descending)\n"
        output_text += "="*130 + "\n\n"
        
        # Column headers
        output_text += f"{'Event':<8} {'Reco ID':<12} {'True ID':<12} {'Reco Charge':<15} {'Matched Pts':<15} {'Total Pts':<12} {'Purity':<12} {'Status':<20}\n"
        output_text += "-"*130 + "\n"
        
        zero_pur_count = 0
        low_pur_count = 0
        good_pur_count = 0
        
        for idx, row in df.iterrows():
            reco_id = row['reco_cluster_id']
            true_id = row['true_cluster_id']
            reco_charge = row['total_reco_cluster_charge']
            matched_pts = row['matched_reco_points']
            total_pts = row['total_reco_points']
            purity = row['purity']
            
            if purity == 0:
                status = "ZERO PURITY"
                zero_pur_count += 1
            elif purity < 0.5:
                status = "LOW PUR (<0.5)"
                low_pur_count += 1
            else:
                status = "Good"
                good_pur_count += 1
            
            output_text += f"{event:<8} {reco_id:<12.2f} {true_id:<12.2f} {reco_charge:<15.2f} {matched_pts:<15} {total_pts:<12} {purity:<12.4f} {status:<20}\n"
        
        output_text += "-"*130 + "\n\n"
        
        # Summary counts
        output_text += "SUMMARY:\n"
        output_text += f"  Total pairs: {len(df)}\n"
        output_text += f"  Zero purity: {zero_pur_count}\n"
        output_text += f"  Low purity (<0.5): {low_pur_count}\n"
        output_text += f"  Good purity (≥0.5): {good_pur_count}\n"
        output_text += "\n" + "="*130 + "\n"
        
        # Print to console
        print(output_text)
        
        # Save to file
        table_file = event_output_dir / "PurityTable.txt"
        with open(table_file, 'w') as f:
            f.write(output_text)
        
        print(f"Saved: {table_file}\n")



def PrintPuritySummaryTable(all_purity_results, output_dir):
    """
    Print and save SUMMARY purity table aggregating across ALL files and ALL events.
    Saves to top-level output_dir (not nested in file/event subdirectories).
    """
    
    if len(all_purity_results) == 0:
        print("No purity results for summary table")
        return
    
    output_dir = Path(output_dir)
    
    # Convert to DataFrame and sort
    df = pd.DataFrame(all_purity_results)
    df = df.sort_values('total_reco_cluster_charge', ascending=False)
    
    # Prepare output text
    output_text = "\n" + "="*140 + "\n"
    output_text += "SUMMARY PURITY TABLE - ALL FILES AND ALL EVENTS\n"
    output_text += "Sorted by Reco Cluster Charge (descending)\n"
    output_text += "="*140 + "\n\n"
    
    # Column headers
    output_text += f"{'Event':<8} {'File':<30} {'Reco ID':<12} {'True ID':<12} {'Reco Charge':<15} {'Matched Pts':<15} {'Total Pts':<12} {'Purity':<12} {'Status':<20}\n"
    output_text += "-"*140 + "\n"
    
    zero_pur_count = 0
    low_pur_count = 0
    good_pur_count = 0
    
    for idx, row in df.iterrows():
        # Extract numeric event ID from string identifier if needed
        event_str = str(row['event'])
        event = int(event_str.split('_')[-1]) if '_' in event_str else int(event_str)
        reco_id = row['reco_cluster_id']
        true_id = row['true_cluster_id']
        reco_charge = row['total_reco_cluster_charge']
        matched_pts = row['matched_reco_points']
        total_pts = row['total_reco_points']
        purity = row['purity']
        
        # Try to extract file name from context
        file_name = "unknown"
        
        if purity == 0:
            status = "ZERO PURITY"
            zero_pur_count += 1
        elif purity < 0.5:
            status = "LOW PUR (<0.5)"
            low_pur_count += 1
        else:
            status = "Good"
            good_pur_count += 1
        
        output_text += f"{event:<8} {file_name:<30} {reco_id:<12.2f} {true_id:<12.2f} {reco_charge:<15.2f} {matched_pts:<15} {total_pts:<12} {purity:<12.4f} {status:<20}\n"
    
    output_text += "-"*140 + "\n\n"
    
    # Summary statistics
    output_text += "SUMMARY STATISTICS:\n"
    output_text += f"  Total pairs: {len(df)}\n"
    output_text += f"  Zero purity: {zero_pur_count}\n"
    output_text += f"  Low purity (<0.5): {low_pur_count}\n"
    output_text += f"  Good purity (≥0.5): {good_pur_count}\n"
    
    purities = df['purity'].values
    output_text += f"\n[PURITY STATISTICS]\n"
    output_text += f"  Mean:                {np.mean(purities):.4f}\n"
    output_text += f"  Std Dev:             {np.std(purities):.4f}\n"
    output_text += f"  Median:              {np.median(purities):.4f}\n"
    output_text += f"  Min:                 {np.min(purities):.4f}\n"
    output_text += f"  Max:                 {np.max(purities):.4f}\n"
    output_text += f"  25th Percentile:     {np.percentile(purities, 25):.4f}\n"
    output_text += f"  75th Percentile:     {np.percentile(purities, 75):.4f}\n"
    
    output_text += "\n" + "="*140 + "\n"
    
    # Print to console
    print(output_text)
    
    # Save to file
    table_file = output_dir / "SUMMARY_PurityTable.txt"
    with open(table_file, 'w') as f:
        f.write(output_text)
    
    print(f"Saved: {table_file}\n")




