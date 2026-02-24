
import os

file_path = r'c:\Users\CASH\Desktop\hustlelink-mzansi\backend\app\routes\marketplace.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    stripped = line.strip()
    if stripped == 'return error_response(f"Field \'{field}\' is required", 400, "bad_request")':
        indent = line[:line.find('return')]
        new_lines.append(f"{indent}return error_response(\n")
        new_lines.append(f"{indent}    f\"Field '{{field}}' is required\", 400, \"bad_request\"\n")
        new_lines.append(f"{indent})\n")
    elif stripped == 'return error_response("Unauthorized or account suspended", 403, "forbidden")':
        indent = line[:line.find('return')]
        new_lines.append(f"{indent}return error_response(\n")
        new_lines.append(f"{indent}    \"Unauthorized or account suspended\", 403, \"forbidden\"\n")
        new_lines.append(f"{indent})\n")
    elif stripped == 'return error_response("Service not found or inactive", 404, "not_found")':
        indent = line[:line.find('return')]
        new_lines.append(f"{indent}return error_response(\n")
        new_lines.append(f"{indent}    \"Service not found or inactive\", 404, \"not_found\"\n")
        new_lines.append(f"{indent})\n")
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Updated marketplace.py")
