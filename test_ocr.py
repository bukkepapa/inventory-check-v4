import sys
import os
from paddleocr import PaddleOCR
import fitz
import numpy as np
from PIL import Image
import pandas as pd

# Set encoding for console output
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='japan')

pdf_path = r"c:\Users\PC_User\Desktop\Antigravity\在庫引当チェックツール_vr3\PDF ファイル\受注一覧リスト必須項目.pdf"

def get_best_text_below(texts, boxes, anchor_text, x_range=20, y_limit=100):
    """Find text directly below an anchor text within a certain x range"""
    anchor_box = None
    for i, t in enumerate(texts):
        if anchor_text in t:
            anchor_box = boxes[i]
            break
    
    if not anchor_box:
        return []
    
    anchor_x = (anchor_box[0][0] + anchor_box[1][0]) / 2
    anchor_bottom = anchor_box[2][1]
    
    candidates = []
    for i, box in enumerate(boxes):
        box_x = (box[0][0] + box[1][0]) / 2
        box_top = box[0][1]
        
        if abs(box_x - anchor_x) < x_range and box_top > anchor_bottom and (box_top - anchor_bottom) < y_limit:
            candidates.append((i, box_top))
    
    candidates.sort(key=lambda x: x[1])
    return [texts[c[0]] for c in candidates]

def process_pdf(path):
    doc = fitz.open(path)
    all_extracted_data = []
    
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_np = np.array(img)
        
        result = ocr.ocr(img_np)
        if not result or result[0] is None:
            continue

        lines = result[0]
        boxes = []
        texts = []
        for line in lines:
            if line and line[1] and line[1][0] is not None:
                boxes.append(line[0])
                texts.append(line[1][0])
            else:
                print(f"Skipping empty line: {line}")
        
        # DEBUG: Print all texts with their rough coordinates
        print(f"\n--- Page {page_index+1} RAW TEXT ---")
        for i, t in enumerate(texts):
            print(f"[{i:03}] {t:20} at {boxes[i][0]}")
        print("----------------------------\n")
        
        # 1. Customer Info
        # Find "出荷先"
        below_shukkasaki = get_best_text_below(texts, boxes, "出荷先")
        customer_code = None
        customer_name = None
        if below_shukkasaki:
            # First one likely code, second likely name
            for t in below_shukkasaki:
                if t is None: continue
                clean_t = "".join(filter(str.isdigit, t))
                if len(clean_t) == 9:
                    customer_code = clean_t
                elif customer_code and not customer_name:
                    customer_name = t
        
        print(f"Page {page_index+1} - Customer: {customer_code} ({customer_name})")
        
        # 2. Table data
        # Find columns for "受注品目" and "数量"
        prod_col_x = None
        qty_col_x = None
        table_top_y = None
        
        for i, t in enumerate(texts):
            if "受注品目" in t:
                prod_col_x = (boxes[i][0][0] + boxes[i][1][0]) / 2
                table_top_y = boxes[i][2][1]
            if "数量" in t:
                qty_col_x = (boxes[i][0][0] + boxes[i][1][0]) / 2
        
        if prod_col_x and qty_col_x:
            # Extract rows
            # Group by y coordinate roughly
            rows = {}
            for i, box in enumerate(boxes):
                top = box[0][1]
                if top > table_top_y:
                    # Group within 10px
                    found_row = False
                    for y_key in rows.keys():
                        if abs(top - y_key) < 15:
                            rows[y_key].append(i)
                            found_row = True
                            break
                    if not found_row:
                        rows[top] = [i]
            
            for y in sorted(rows.keys()):
                row_indices = rows[y]
                row_texts = [texts[idx] for idx in row_indices]
                row_boxes = [boxes[idx] for idx in row_indices]
                
                prod_code = None
                qty = None
                
                for idx in row_indices:
                    box = boxes[idx]
                    txt = texts[idx]
                    center_x = (box[0][0] + box[1][0]) / 2
                    
                    if abs(center_x - prod_col_x) < 50:
                        # Likely product code (should be 7 digits)
                        if len("".join(filter(str.isdigit, txt))) >= 5:
                            prod_code = "".join(filter(str.isdigit, txt))
                    if abs(center_x - qty_col_x) < 50:
                        # Likely quantity
                        try:
                            qty = float(txt.replace(",", ""))
                        except:
                            pass
                
                if prod_code and qty is not None:
                    print(f"  Row: {prod_code} -> {qty}")
                    all_extracted_data.append({
                        '顧客コード': customer_code,
                        '顧客名': customer_name,
                        '商品コード': prod_code,
                        '発注数量': int(qty)
                    })
                    
    doc.close()
    return pd.DataFrame(all_extracted_data)

if __name__ == "__main__":
    df = process_pdf(pdf_path)
    print("\nEXTRACTED DATA:")
    print(df)
