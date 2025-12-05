import os
import re
from pathlib import Path
from docx import Document

def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        content = []
        for para in doc.paragraphs:
            if para.text.strip():
                content.append(para.text)
        return "\n".join(content)
    except Exception as e:
        return f"Error: {e}"

file_path = Path("data/codexes/thai_CrimCodeThai.docx")
if not file_path.exists():
    print(f"File not found: {file_path}")
else:
    content = extract_text_from_docx(file_path)
    
    print(f"File size: {len(content)} chars")
    
    # Check for keywords
    keywords = ["murder", "kill", "homicide", "manslaughter", "убийство", "убить", "Section 288", "Section 289"]
    print("\nKeywords search:")
    for kw in keywords:
        matches = len(re.findall(re.escape(kw), content, re.IGNORECASE))
        print(f"'{kw}': {matches} matches")
        
    # Show context for Section 288 (usually murder)
    print("\nContext for 'Section 288':")
    match = re.search(r"(Section\s+288.*?(?=Section|\Z))", content, re.DOTALL | re.IGNORECASE)
    if match:
        print(match.group(1)[:500] + "...")
    else:
        print("Section 288 not found")

    # Show first 500 chars to check format
    print("\nFirst 500 chars:")
    print(content[:500])

