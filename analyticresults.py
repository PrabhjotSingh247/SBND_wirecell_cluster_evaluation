import numpy as np
import pandas as pd
from pathlib import Path

def AnalyticResults(all_matched_pairs, output_dir=None):
    """
    Perform comprehensive statistical analysis on completeness and purity matched pairs.
    Optionally save results to a text file in output_dir.
    """
    if len(all_matched_pairs) == 0:
        print("No matched pairs to analyze")
        return
    
    # Extract completeness and purity values
    completenesses = [p['completeness_energy_weighted'] for p in all_matched_pairs]
    purities = [p['purity'] for p in all_matched_pairs]
    
    # Prepare output text
    output_text = ""
    output_text += "\n" + "="*70 + "\n"
    output_text += "ANALYTIC RESULTS - Statistical Analysis\n"
    output_text += "="*70 + "\n"
    
    # Completeness Statistics
    output_text += "\n[COMPLETENESS STATISTICS]\n"
    output_text += f"  Mean:                {np.mean(completenesses):.4f}\n"
    output_text += f"  Std Dev:             {np.std(completenesses):.4f}\n"
    output_text += f"  Median:              {np.median(completenesses):.4f}\n"
    output_text += f"  Min:                 {np.min(completenesses):.4f}\n"
    output_text += f"  Max:                 {np.max(completenesses):.4f}\n"
    output_text += f"  25th Percentile:     {np.percentile(completenesses, 25):.4f} (25% of clusters below this)\n"
    output_text += f"  75th Percentile:     {np.percentile(completenesses, 75):.4f} (75% of clusters below this)\n"
    output_text += f"  95th Percentile:     {np.percentile(completenesses, 95):.4f} (95% of clusters below this)\n"
    
    # Purity Statistics
    output_text += "\n[PURITY STATISTICS]\n"
    output_text += f"  Mean:                {np.mean(purities):.4f}\n"
    output_text += f"  Std Dev:             {np.std(purities):.4f}\n"
    output_text += f"  Median:              {np.median(purities):.4f}\n"
    output_text += f"  Min:                 {np.min(purities):.4f}\n"
    output_text += f"  Max:                 {np.max(purities):.4f}\n"
    output_text += f"  25th Percentile:     {np.percentile(purities, 25):.4f} (25% of clusters below this)\n"
    output_text += f"  75th Percentile:     {np.percentile(purities, 75):.4f} (75% of clusters below this)\n"
    output_text += f"  95th Percentile:     {np.percentile(purities, 95):.4f} (95% of clusters below this)\n"
    
    # Combined Statistics
    output_text += "\n[COMBINED STATISTICS]\n"
    combined_scores = [(e + p) / 2 for e, p in zip(completenesses, purities)]
    output_text += f"  Mean Combined Score: {np.mean(combined_scores):.4f}\n"
    output_text += f"  Std Dev Combined:    {np.std(combined_scores):.4f}\n"
    
    # Count statistics
    output_text += "\n[PERFORMANCE COUNTS]\n"
    high_eff = sum(1 for e in completenesses if e > 0.9)
    high_pur = sum(1 for p in purities if p > 0.9)
    eff_80 = sum(1 for e in completenesses if e > 0.8)
    pur_80 = sum(1 for p in purities if p > 0.8)
    good_both = sum(1 for e, p in zip(completenesses, purities) if e > 0.8 and p > 0.8)
    
    output_text += f"  Clusters with Eff > 0.9:              {high_eff} ({100*high_eff/len(completenesses):.1f}%)\n"
    output_text += f"  Clusters with Pur > 0.9:              {high_pur} ({100*high_pur/len(purities):.1f}%)\n"
    output_text += f"  Clusters with Eff > 0.8:              {eff_80} ({100*eff_80/len(completenesses):.1f}%)\n"
    output_text += f"  Clusters with Pur > 0.8:              {pur_80} ({100*pur_80/len(purities):.1f}%)\n"
    output_text += f"  Clusters with BOTH Eff>0.8 & Pur>0.8: {good_both} ({100*good_both/len(completenesses):.1f}%)\n"
    
    # Correlation
    output_text += "\n[CORRELATION]\n"
    correlation = np.corrcoef(completenesses, purities)[0, 1]
    output_text += f"  Completeness-Purity Correlation: {correlation:.4f}\n"
    
    output_text += "\n" + "="*70 + "\n"
    
    # Print to console
    print(output_text)
    
    # Save to file if output_dir is provided
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        summary_file = output_dir / "-200_Summary.txt"
        with open(summary_file, 'w') as f:
            f.write(output_text)
        

