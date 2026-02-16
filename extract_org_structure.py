#!/usr/bin/env python3
import sys
sys.path.insert(0, r'c:\Users\r.petniunas\Downloads\AI\rpetni-AE.CAP.1.1\Onboarding_agent')

from PyPDF2 import PdfReader

pdf_path = r'c:\Users\r.petniunas\Downloads\AI\rpetni-AE.CAP.1.1\Internal rules\org structure.pdf'

try:
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        print(text)
except Exception as e:
    print(f"Error: {e}")
