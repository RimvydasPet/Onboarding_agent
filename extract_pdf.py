import sys
from PyPDF2 import PdfReader

pdf_path = r'c:\Users\r.petniunas\Downloads\AI\rpetni-AE.CAP.1.1\Internal rules\org structure.pdf'

with open(pdf_path, "rb") as f:
    reader = PdfReader(f)
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            sys.stdout.buffer.write(f"--- Page {page_num + 1} ---\n".encode('utf-8'))
            sys.stdout.buffer.write(text.encode('utf-8', errors='replace'))
            sys.stdout.buffer.write(b"\n\n")
