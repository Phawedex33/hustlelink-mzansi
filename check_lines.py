"""
Check for lines exceeding the PEP 8 character limit (79 chars).
"""

import os

FILE_DIR = r"c:\Users\CASH\Desktop\hustlelink-mzansi\backend"
FILE_NAME = r"app\routes\marketplace.py"
FILE_PATH = os.path.join(FILE_DIR, FILE_NAME)

if os.path.exists(FILE_PATH):
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            length = len(line.rstrip("\n\r"))
            if length > 79:
                print(f"Line {i+1}: {length} characters")
                print(f"  {line.strip()}")
else:
    print("File not found")
