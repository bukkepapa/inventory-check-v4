import fitz  # PyMuPDF
import os

pdf_path = r"c:\Users\PC_User\Desktop\Antigravity\在庫引当チェックツール_vr3\PDF ファイル\受注一覧リスト必須項目.pdf"
output_image = "pdf_page_1.png"

if os.path.exists(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)  # first page
    pix = page.get_pixmap()
    pix.save(output_image)
    print(f"Saved first page to {output_image}")
else:
    print(f"File not found: {pdf_path}")
