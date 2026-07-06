"""
Module to print bee-display links for mabc*.zip files.
Runs bee-upload.sh to generate links for mabc files.
"""

from pathlib import Path
import glob
import subprocess
import os


# Path to bee-upload.sh script
BEE_UPLOAD_SCRIPT = Path("/exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/bee-upload.sh")


def print_bee_display_link(input_dir):
    """
    Print bee-display links by running bee-upload.sh if mabc*.zip files exist.

    Parameters
    ----------
    input_dir : str or Path
        Path to the input directory containing mabc*.zip files.
        The function extracts the file name (e.g., 'file1') from the path.

    Returns
    -------
    None
        Prints the bee-display links to stdout if files exist, otherwise skips silently.
    """
    input_dir = Path(input_dir)

    # Extract file name from path (e.g., 'file1' from '.../file1' or '.../file1/data')
    file_name = input_dir.name
    if file_name == 'data':
        file_name = input_dir.parent.name

    # Search for mabc*.zip files in the input directory
    mabc_files = sorted(glob.glob(str(input_dir / "mabc*.zip")))

    if not mabc_files:
        # No mabc files found, skip silently
        return

    # Check if bee-upload.sh exists
    if not BEE_UPLOAD_SCRIPT.exists():
        print(f"\nWarning: bee-upload.sh not found at {BEE_UPLOAD_SCRIPT}")
        return

    print(f"\n{'='*70}")
    print(f"BEE-DISPLAY LINKS for {file_name}")
    print(f"{'='*70}")

    # Run bee-upload.sh in the input directory
    try:
        # Save current directory
        original_dir = os.getcwd()

        # Change to input directory
        os.chdir(input_dir)

        # Run bee-upload.sh
        result = subprocess.run(
            ['bash', str(BEE_UPLOAD_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=300
        )

        # Change back to original directory
        os.chdir(original_dir)

        # Extract URLs from output
        if result.stdout:
            # Parse the output for URLs
            for line in result.stdout.split('\n'):
                if 'https://' in line:
                    print(f"  {line.strip()}")

        if result.returncode != 0:
            print(f"  Error running bee-upload.sh:")
            for line in result.stderr.split('\n')[:5]:  # Show first 5 error lines
                if line.strip():
                    print(f"    {line.strip()}")

    except subprocess.TimeoutExpired:
        print(f"  Error: bee-upload.sh timed out (exceeded 5 minutes)")
    except Exception as e:
        print(f"  Error running bee-upload.sh: {str(e)}")
    finally:
        # Ensure we're back in the original directory
        try:
            os.chdir(original_dir)
        except:
            pass

    print()
