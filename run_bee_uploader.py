#!/usr/bin/env python3
"""
Standalone script to upload .zip files to BEE and save links to a text file.
Run this independently after your analysis is complete.

Usage:
    python run_bee_uploader.py
"""

from pathlib import Path
from printbeelink import upload_bee_files_and_save


def main():
    # Configuration
    parent_dir = Path("/exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/batch_results/2view")
    bee_script = Path("/exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/bee-upload-with-truth-3viewdeadarea.sh")
    output_dir = Path("/exp/sbnd/data/users/prabhjot/wirecell_clustering/cluster_evaluation")
    output_file = output_dir / "bee_links_final.txt"

    print("\n" + "="*80)
    print("BEE UPLOADER - STANDALONE")
    print("="*80)

    print(f"\nConfiguration:")
    print(f"  Parent directory: {parent_dir}")
    print(f"  BEE script: {bee_script}")
    print(f"  Output file: {output_file}")

    # Check if directories exist
    if not parent_dir.exists():
        print(f"\n❌ ERROR: Parent directory not found: {parent_dir}")
        return False

    if not bee_script.exists():
        print(f"\n❌ ERROR: BEE script not found: {bee_script}")
        return False

    # Run uploader
    print(f"\n{'='*80}")
    print("Starting BEE upload process...")
    print(f"{'='*80}\n")

    try:
        bee_links = upload_bee_files_and_save(parent_dir, bee_script, str(output_file))

        # Summary
        total_links = sum(len(links) for links in bee_links.values())

        print(f"\n{'='*80}")
        print("✓ UPLOAD COMPLETE")
        print(f"{'='*80}")
        print(f"\nSummary:")
        print(f"  Files processed: {len(bee_links)}")
        print(f"  Total BEE links: {total_links}")
        print(f"  Output file: {output_file}")

        # Show preview
        if output_file.exists():
            print(f"\n{'='*80}")
            print("FILE PREVIEW (first 30 lines)")
            print(f"{'='*80}\n")
            with open(output_file) as f:
                lines = f.readlines()[:30]
                print("".join(lines))

        print(f"\n✓ Done! Check {output_file} for all links.")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
