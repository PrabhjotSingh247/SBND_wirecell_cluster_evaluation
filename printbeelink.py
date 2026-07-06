import subprocess
import os
from pathlib import Path


def upload_bee_files_and_save(parent_dir, bee_script_path, output_file="bee_links.txt"):
    """
    Upload .zip files from each file subdirectory to BEE and save links to a text file.

    Parameters:
    - parent_dir: Parent directory containing file subdirectories (file1/, file2/, ...)
    - bee_script_path: Path to the bee-upload-with-truth-*.sh script
    - output_file: Output text file to save BEE links (default: bee_links.txt)

    Returns:
    - Dictionary mapping file names to lists of BEE URLs
    """
    parent_dir = Path(parent_dir)
    bee_script_path = Path(bee_script_path)

    if not bee_script_path.exists():
        print(f"ERROR: BEE script not found: {bee_script_path}")
        return {}

    bee_links = {}

    for file_subdir in sorted(parent_dir.iterdir()):
        if not file_subdir.is_dir():
            continue

        file_name = file_subdir.name
        zip_files = list(file_subdir.glob("*.zip"))

        if not zip_files:
            continue

        print(f"\n{'='*70}")
        print(f"Uploading {file_name} ({len(zip_files)} .zip file(s)) to BEE")
        print(f"{'='*70}")

        bee_links[file_name] = []

        for zip_file in sorted(zip_files):
            print(f"\n  {zip_file.name}...", end=" ", flush=True)

            try:
                original_cwd = os.getcwd()
                os.chdir(file_subdir)

                result = subprocess.run(
                    ["bash", str(bee_script_path)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                os.chdir(original_cwd)

                if result.returncode != 0:
                    print(f"FAILED")
                    continue

                # Extract BEE URL from output
                bee_url = None
                for line in reversed(result.stdout.split('\n')):
                    if 'https://' in line or 'http://' in line:
                        bee_url = line.strip()
                        break

                if bee_url:
                    print(f"✓")
                    bee_links[file_name].append({'zip': zip_file.name, 'url': bee_url})
                else:
                    print(f"Could not extract URL")

            except Exception as e:
                print(f"ERROR: {e}")
                os.chdir(original_cwd)

        if bee_links[file_name]:
            print(f"\n  {file_name} BEE links:")
            for link_info in bee_links[file_name]:
                print(f"    {link_info['url']}")

    # Save to file
    with open(output_file, 'w') as f:
        f.write("BEE UPLOAD LINKS\n")
        f.write("="*80 + "\n\n")

        for file_name, links in bee_links.items():
            if links:
                f.write(f"{file_name}:\n")
                f.write("-"*80 + "\n")
                for link_info in links:
                    f.write(f"  {link_info['zip']}\n")
                    f.write(f"    {link_info['url']}\n\n")
                f.write("\n")

    print(f"\n{'='*70}")
    print(f"BEE links saved to: {output_file}")
    print(f"{'='*70}\n")

    return bee_links
