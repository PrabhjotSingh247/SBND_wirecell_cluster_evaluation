"""Flip SAMPLE_NAME = "<old>" -> SAMPLE_NAME = "<new>" in a notebook's raw JSON
text (not a json round-trip -- see feedback_strip_notebook_outputs memory).
Usage: python3 _flip_sample_name.py <notebook_path> <old_value> <new_value>
"""
import sys

path, old_value, new_value = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding="utf-8").read()
old = f'SAMPLE_NAME = \\"{old_value}\\"'
new = f'SAMPLE_NAME = \\"{new_value}\\"'
n = text.count(old)
assert n == 1, f"expected 1 occurrence of {old!r} in {path}, found {n}"
open(path, "w", encoding="utf-8").write(text.replace(old, new))
print(f"{path}: {old!r} -> {new!r}")
