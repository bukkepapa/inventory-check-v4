import pdfplumber
import os

pdf_path = r"c:\Users\PC_User\Desktop\Antigravity\在庫引当チェックツール_vr3\PDF ファイル\受注一覧リスト必須項目.pdf"

if os.path.exists(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"--- Page {i+1} ---")
            text = page.extract_text()
            print(text)
            
            # Also try to extract tables if any
            tables = page.extract_tables()
            for j, table in enumerate(tables):
                print(f"Table {j+1}:")
                for row in table:
                    print(row)
else:
    print(f"File not found: {pdf_path}")
