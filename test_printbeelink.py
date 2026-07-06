#!/usr/bin/env python3
"""
Test script for printbeelink.py
Tests BEE link printing functionality.
"""

import os
import sys
from pathlib import Path
from printbeelink import upload_bee_files_and_save


def test_with_real_directories():
    """Test with actual file directories and BEE script."""
    print("="*80)
    print("TEST: Upload BEE Files and Save Links")
    print("="*80)

    # Path to parent directory with files
    parent_dir = Path("/exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/batch_results/2view")

    # Path to BEE upload script
    bee_script = Path("/exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/bee-upload-with-truth-3viewdeadarea.sh")

    # Output file for links
    output_file = "bee_links_output.txt"

    print(f"\nConfiguration:")
    print(f"  Parent directory: {parent_dir}")
    print(f"  Exists: {parent_dir.exists()}")
    print(f"  BEE script: {bee_script}")
    print(f"  Exists: {bee_script.exists()}")
    print(f"  Output file: {output_file}")

    # Check for .zip files in directories
    print(f"\nScanning for .zip files:")
    zip_count = 0
    for subdir in sorted(parent_dir.iterdir()):
        if subdir.is_dir():
            zips = list(subdir.glob("*.zip"))
            if zips:
                print(f"  {subdir.name}: {len(zips)} .zip file(s)")
                zip_count += len(zips)

    if zip_count == 0:
        print("  ❌ No .zip files found in any subdirectories")
        print("\n  To test, you need:")
        print("    1. .zip files in file subdirectories (file1/, file2/, etc.)")
        print("    2. BEE upload script executable")
        return False

    print(f"\n  Total: {zip_count} .zip files found")

    # Run the uploader
    print(f"\n{'='*80}")
    print("Starting BEE upload process...")
    print(f"{'='*80}\n")

    try:
        bee_links = upload_bee_files_and_save(parent_dir, bee_script, output_file)

        # Print summary
        print(f"\n{'='*80}")
        print("UPLOAD COMPLETE")
        print(f"{'='*80}\n")

        total_links = sum(len(links) for links in bee_links.values())
        print(f"Total BEE links collected: {total_links}")
        print(f"Links saved to: {output_file}")

        # Show file contents
        if Path(output_file).exists():
            print(f"\n{'-'*80}")
            print("File contents:")
            print(f"{'-'*80}\n")
            with open(output_file) as f:
                print(f.read())

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dry_run():
    """Dry run without actually uploading - just show what would happen."""
    print("\n" + "="*80)
    print("DRY RUN: Show structure without uploading")
    print("="*80)

    parent_dir = Path("/exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/batch_results/2view")

    print(f"\nDirectory structure:")
    for subdir in sorted(parent_dir.iterdir()):
        if subdir.is_dir():
            zips = list(subdir.glob("*.zip"))
            if zips:
                print(f"\n  {subdir.name}/ ({len(zips)} .zip files):")
                for z in sorted(zips):
                    print(f"    - {z.name}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PRINTBEELINK TEST SUITE")
    print("="*80 + "\n")

    # First show structure
    test_dry_run()

    # Then try actual upload
    print("\n")
    success = test_with_real_directories()

    if not success:
        print("\n" + "="*80)
        print("INSTRUCTIONS TO PREPARE FOR TESTING:")
        print("="*80)
        print("""
1. Ensure you have .zip files in your file directories:
   /exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/batch_results/2view/file1/
   /exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/batch_results/2view/file2/
   etc.

2. Verify the BEE upload script exists and is executable:
   chmod +x /exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/bee-upload-with-truth-3viewdeadarea.sh

3. Run the test again:
   python test_printbeelink.py

4. Or use directly in your notebook:
   from printbeelink import upload_bee_files_and_save
   bee_links = upload_bee_files_and_save(PARENT_DIR, bee_script_path, "bee_links.txt")
        """)
