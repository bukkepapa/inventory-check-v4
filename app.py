import streamlit as st
import pandas as pd
from io import BytesIO
import base64
import numpy as np
from PIL import Image
import fitz
from paddleocr import PaddleOCR
import re

# --- UI Custom Styling ---
def apply_custom_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');

        :root {
            --primary: #0f172a;
            --accent: #2563eb;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .stApp {
            background-color: var(--bg);
            font-family: 'Inter', 'Noto Sans JP', sans-serif;
            color: var(--text-main);
        }

        /* Header Styling */
        .main-header {
            padding: 3rem 1rem;
            text-align: center;
            background: radial-gradient(circle at top, #f1f5f9 0%, var(--bg) 100%);
            margin-bottom: 2rem;
        }

        .main-header h1 {
            color: var(--primary);
            font-weight: 800;
            margin-bottom: 0.75rem;
            font-size: 3rem;
            letter-spacing: -0.025em;
        }

        .main-header p {
            color: var(--text-muted);
            font-size: 1.125rem;
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.6;
        }

        .version-badge {
            background: var(--primary);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: inline-block;
        }

        /* Card Elements */
        .stFileUploader {
            background: white;
            padding: 1.5rem;
            border-radius: 1rem;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
        }

        .upload-title {
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 1.25rem;
            display: flex;
            align-items: center;
            gap: 0.625rem;
            font-size: 1.1rem;
        }

        /* Button Styling */
        .stButton > button {
            background: var(--primary) !important;
            color: white !important;
            border: none !important;
            padding: 0.875rem 2rem !important;
            border-radius: 0.75rem !important;
            font-weight: 600 !important;
            font-size: 1.125rem !important;
            width: 100% !important;
            transition: var(--transition) !important;
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1) !important;
        }

        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1) !important;
            background: #1e293b !important;
        }

        /* Section Title */
        .section-title {
            font-weight: 700;
            color: var(--primary);
            margin: 2.5rem 0 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .section-title::before {
            content: "";
            width: 4px;
            height: 24px;
            background: var(--accent);
            border-radius: 2px;
        }

        /* Results Display */
        .stDataFrame {
            background: white;
            padding: 1rem;
            border-radius: 1rem;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
        }

        .stAlert {
            border-radius: 1rem !important;
            border: 1px solid #e2e8f0 !important;
        }

        /* Expander */
        .stExpander {
            background: white !important;
            border: 1px solid var(--border) !important;
            border-radius: 1rem !important;
            margin-top: 2rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

def load_inventory_file(file):
    """速報倉庫在庫ファイルを読み込む"""
    try:
        file_ext = file.name.split('.')[-1].lower()
        if file_ext == 'csv':
            df = pd.read_csv(file, header=None, usecols=[1, 4, 8, 10, 13, 22], encoding='cp932')
            df.columns = ['保管場所', 'ロケーション', '商品コード', '入数', '倉庫在庫数', '入庫予定']
            df = df[df['保管場所'] == 'A309001']
            # ロケーションが9で始まる不良在庫を除外
            df['ロケーション'] = df['ロケーション'].astype(str)
            df = df[~df['ロケーション'].str.startswith('9')]
        elif file_ext in ['xlsx', 'xls']:
            df = pd.read_excel(file, header=None, usecols=[1, 4, 8, 10, 13, 22])
            df.columns = ['保管場所', 'ロケーション', '商品コード', '入数', '倉庫在庫数', '入庫予定']
            df = df[df['保管場所'] == 'A309001']
            # ロケーションが9で始まる不良在庫を除外
            df['ロケーション'] = df['ロケーション'].astype(str)
            df = df[~df['ロケーション'].str.startswith('9')]
        else:
            raise ValueError(f"サポートされていないファイル形式です: {file_ext}")
        
        for col in ['倉庫在庫数', '入数', '入庫予定']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        df['倉庫在庫数'] = df['倉庫在庫数'] + (df['入庫予定'] * df['入数'])
        df = df.dropna(subset=['商品コード'])
        df['商品コード'] = df['商品コード'].astype(str).str.lstrip('0')
        return df[['商品コード', '倉庫在庫数']]
    except Exception as e:
        raise Exception(f"倉庫在庫ファイルの読み込みエラー: {str(e)}")

def process_pdf_order(file):
    """PDF受注一覧を解析する"""
    try:
        # Create fresh OCR instance each time to avoid memory issues
        ocr = PaddleOCR(use_angle_cls=True, lang='japan')
        doc = fitz.open(stream=file.read(), filetype="pdf")
        extracted_data = []
        
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            # Higher resolution for OCR
            zoom = 2.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_np = np.array(img)
            
            # OCR execution with error handling
            try:
                result = ocr.ocr(img_np)
            except Exception as ocr_err:
                st.warning(f"ページ {page_index+1} のOCR処理に失敗しました: {str(ocr_err)}")
                continue
                
            if not result or not result[0]:
                continue
                
            lines = result[0]
            boxes = [line[0] for line in lines]
            texts = [line[1][0] for line in lines]
            
            # Helper to find text below
            def find_below(anchor_pattern, x_range=50, y_limit=100):
                anchor_idx = -1
                for i, t in enumerate(texts):
                    if t and re.search(anchor_pattern, t):
                        anchor_idx = i
                        break
                if anchor_idx == -1: return []
                
                ax = (boxes[anchor_idx][0][0] + boxes[anchor_idx][1][0]) / 2
                ab = boxes[anchor_idx][2][1]
                
                candidates = []
                for i, b in enumerate(boxes):
                    if i == anchor_idx: continue
                    bx = (b[0][0] + b[1][0]) / 2
                    bt = b[0][1]
                    if abs(bx - ax) < x_range and bt > ab and (bt - ab) < y_limit:
                        candidates.append((i, bt))
                candidates.sort(key=lambda x: x[1])
                return [texts[c[0]] for c in candidates]

            # 1. Customer Info
            cust_texts = find_below("出荷先")
            customer_code = "不明"
            customer_name = "不明"
            for ct in cust_texts:
                code_match = re.search(r'\d{9}', ct)
                if code_match:
                    customer_code = code_match.group()
                elif customer_code != "不明" and customer_name == "不明":
                    customer_name = ct

            # 2. Table Headers
            prod_x = -1
            qty_x = -1
            header_y = -1
            print(f"DEBUG Page {page_index+1}: Pix size {pix.width}x{pix.height}")
            for i, t in enumerate(texts):
                if not t: continue
                # Fuzzy header check
                if any(k in t for k in ["受注品目", "品目", "商品"]):
                    prod_x = (boxes[i][0][0] + boxes[i][1][0]) / 2
                    header_y = boxes[i][2][1]
                    print(f"DEBUG: Found prod_x at {prod_x}, y={header_y} ('{t}')")
                if any(k in t for k in ["数量", "受注数"]):
                    qty_x = (boxes[i][0][0] + boxes[i][1][0]) / 2
                    print(f"DEBUG: Found qty_x at {qty_x} ('{t}')")
            
            # If headers are missing, try fallback positions based on common layouts
            if prod_x == -1: prod_x = pix.width * 0.5 / zoom 
            if qty_x == -1: qty_x = pix.width * 0.65 / zoom
            if header_y == -1: header_y = pix.height * 0.25 / zoom
            print(f"DEBUG: Final Extraction Coords: P_X={prod_x}, Q_X={qty_x}, H_Y={header_y}")
            
            # Group lines by row - using a slightly larger variance for hand-scanned notes
            rows = {}
            for i, b in enumerate(boxes):
                try:
                    # Validate box structure before accessing
                    if not b or len(b) < 4 or not b[0] or len(b[0]) < 2:
                        continue
                    top_y = b[0][1]
                    if top_y > (header_y - 10):
                        matched = False
                        for r_y in rows.keys():
                            if abs(top_y - r_y) < 30:
                                rows[r_y].append(i)
                                matched = True
                                break
                        if not matched:
                            rows[top_y] = [i]
                except (IndexError, TypeError):
                    continue
            
            for y in sorted(rows.keys()):
                idx_list = rows[y]
                p_code = None
                qty = None
                for idx in idx_list:
                    try:
                        box = boxes[idx]
                        if not box or len(box) < 2:
                            continue
                        bx = (box[0][0] + box[1][0]) / 2
                        txt = texts[idx]
                    except (IndexError, TypeError):
                        continue
                    if abs(bx - prod_x) < 200: 
                        clean_prod = "".join(filter(str.isdigit, txt))
                        if 4 <= len(clean_prod) <= 12:
                            p_code = clean_prod
                    if abs(bx - qty_x) < 150:
                        try:
                            clean_qty = re.sub(r'[^0-9\.]', '', txt)
                            if clean_qty:
                                qty = int(float(clean_qty))
                        except:
                            pass
                
                if p_code and qty is not None:
                    extracted_data.append({
                        '顧客コード': customer_code,
                        '顧客名': customer_name,
                        '伝票番号': 'PDF受注',
                        '商品コード': p_code.lstrip('0'),
                        '商品名漢字': "PDF抽出商品",
                        '商品名カナ': "",
                        '発注数量': qty,
                        'チェーン店固有エリア': ""
                    })
        
        doc.close()
        return pd.DataFrame(extracted_data)
    except Exception as e:
        import traceback
        st.error(f"詳細エラー:\n{traceback.format_exc()}")
        raise Exception(f"PDFファイルの読み込みエラー ({file.name}): {str(e)}")

def load_order_file(file):
    """受注ファイルを読み込む"""
    encodings = ['utf-8-sig', 'utf-8', 'cp932']
    df = None
    last_error = None
    
    for encoding in encodings:
        try:
            file.seek(0)
            df = pd.read_csv(
                file,
                encoding=encoding,
                sep='\t',
                header=0,
                usecols=[14, 15, 38, 97, 106, 108, 118, 143]
            )
            break
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            raise Exception(f"受注ファイルの読み込みエラー: {str(e)}")
    
    if df is None:
        raise Exception(f"受注ファイルの文字コードエラー: 対応しているエンコーディングでの読み込みに失敗しました。")
    
    try:
        df.columns = ['顧客コード', '顧客名', '伝票番号', '商品コード', '商品名漢字', '商品名カナ', '発注数量', 'チェーン店固有エリア']
        df['発注数量'] = pd.to_numeric(df['発注数量'], errors='coerce').fillna(0).astype(int)
        df = df.dropna(subset=['商品コード'])
        df['商品コード'] = df['商品コード'].astype(str).str.lstrip('0')
        df = df[df['商品コード'] != '30126']
        return df
    except Exception as e:
        raise Exception(f"受注ファイルの形式エラー: {str(e)}")

def calculate_allocation(inventory_df, order_df):
    """在庫引当を計算する"""
    order_summary = order_df.groupby('商品コード').agg({
        '発注数量': 'sum',
        '商品名漢字': 'first',
        '商品名カナ': 'first'
    }).reset_index()
    order_summary.columns = ['商品コード', '受注合計数', '商品名漢字', '商品名カナ']
    order_summary['商品名'] = order_summary['商品名漢字'].fillna(order_summary['商品名カナ']).fillna('')
    order_summary = order_summary[['商品コード', '受注合計数', '商品名']]
    order_summary['商品コード'] = order_summary['商品コード'].astype(str)
    
    allocation_df = order_summary.merge(inventory_df, on='商品コード', how='left')
    allocation_df['倉庫在庫数'] = allocation_df['倉庫在庫数'].fillna(0).astype(int)
    
    # 特殊処理: 0019005
    # 「エラーとして止めない 即利用として表示する 表示名は 品目マスターエラー とする」
    # 在庫に関わらず、引当後在庫を0（不足なし）として扱い、後で表示を切り替える
    allocation_df.loc[allocation_df['商品コード'] == '19005', '引当後在庫'] = 0
    
    # 通常の引当計算
    mask = allocation_df['商品コード'] != '19005'
    allocation_df.loc[mask, '引当後在庫'] = allocation_df.loc[mask, '倉庫在庫数'] - allocation_df.loc[mask, '受注合計数']
    
    return allocation_df

def display_results(allocation_df, order_df):
    """結果を表示する"""
    # 0019005 を抽出
    special_item = allocation_df[allocation_df['商品コード'] == '19005'].copy()
    
    # 通常の不足商品を抽出
    shortage_df = allocation_df[(allocation_df['引当後在庫'] < 0) & (allocation_df['商品コード'] != '19005')].copy()
    
    if shortage_df.empty and special_item.empty:
        success_animation = """
        <style>
        .success-card {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            border-radius: 1.5rem;
            padding: 3rem;
            text-align: center;
            color: white;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            animation: slideIn 0.5s ease-out;
        }
        @keyframes slideIn {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .success-icon { font-size: 4rem; margin-bottom: 1rem; display: block; }
        .success-title { font-size: 2.25rem; font-weight: 700; margin-bottom: 0.5rem; }
        .success-sub { font-size: 1.25rem; opacity: 0.9; }
        </style>
        <div class="success-card">
            <span class="success-icon">✨</span>
            <div class="success-title">在庫充足</div>
            <div class="success-sub">すべての商品の引当が可能です。伝票印字・データ送信を開始できます。</div>
        </div>
        """
        st.markdown(success_animation, unsafe_allow_html=True)
        st.balloons()
    else:
        st.markdown('<div class="section-title">⚠️ 不足商品リスト</div>', unsafe_allow_html=True)
        
        shortage_df['不足数'] = shortage_df['引当後在庫'].abs()
        
        # 伝票番号ごとに1行で展開
        slip_rows = []
        for _, row in shortage_df.iterrows():
            product_code = row['商品コード']
            order_details = order_df[order_df['商品コード'] == product_code][['顧客名', '伝票番号', 'チェーン店固有エリア']].drop_duplicates(subset=['伝票番号'])
            for _, detail in order_details.iterrows():
                slip_rows.append({
                    '商品コード': product_code,
                    '商品名': str(detail.get('チェーン店固有エリア', '')),
                    '倉庫在庫': row['倉庫在庫数'],
                    '受注合計': row['受注合計数'],
                    '不足数': row['不足数'],
                    '伝票番号': str(detail['伝票番号']),
                    '該当顧客名': str(detail['顧客名'])
                })
        
        result_df = pd.DataFrame(slip_rows)
        if not result_df.empty:
            # 伝票番号の昇順ソート
            result_df = result_df.sort_values('伝票番号', ascending=True).reset_index(drop=True)
            
            # 伝票番号の重複チェック（異なる商品で同一伝票番号が存在する場合）
            slip_counts = result_df['伝票番号'].value_counts()
            dup_slips = slip_counts[slip_counts > 1].index
            result_df['重複'] = result_df['伝票番号'].apply(lambda x: '★' if x in dup_slips else '')
        
        st.dataframe(result_df, use_container_width=True)

    # 特殊アイテム（0019005）の表示
    if not special_item.empty:
        st.markdown('<div class="section-title">ℹ️ 即利用アイテム (品目マスターエラー)</div>', unsafe_allow_html=True)
        special_info = []
        for _, row in special_item.iterrows():
            product_code = row['商品コード']
            customers = order_df[order_df['商品コード'] == product_code][['顧客コード', '顧客名']].drop_duplicates()
            customer_codes = ', '.join(customers['顧客コード'].astype(str).tolist())
            customer_names = ', '.join(customers['顧客名'].astype(str).tolist())
            special_info.append({
                '商品コード': '0019005',
                '表示名': '品目マスターエラー',
                '受注合計': row['受注合計数'],
                '状態': '即利用',
                '該当顧客名': customer_names
            })
        st.dataframe(pd.DataFrame(special_info), use_container_width=True)

def main():
    st.set_page_config(
        page_title="不足確認 | Smart Allocation v3",
        page_icon="📦",
        layout="wide"
    )
    
    apply_custom_style()
    
    # Header Section
    st.markdown("""
        <div class="main-header">
            <span class="version-badge">Version 3.0</span>
            <h1>📦 不足確認</h1>
            <p>Smart Allocation - 業務効率を追求した次世代の在庫引当・不足判定ソリューション</p>
        </div>
    """, unsafe_allow_html=True)
    
    # File Uploader Section
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div class="upload-title">📑 速報倉庫在庫ファイル</div>
        """, unsafe_allow_html=True)
        inventory_file = st.file_uploader(
            "Excel / CSV を選択",
            type=['xlsx', 'xls', 'csv'],
            key='inventory',
            label_visibility="collapsed"
        )
    
    with col2:
        st.markdown("""
            <div class="upload-title">📝 受注ファイル (TXT / PDF)</div>
        """, unsafe_allow_html=True)
        order_files = st.file_uploader(
            "ファイルを選択 (複数可)",
            type=['txt', 'pdf'],
            key='order',
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Action Button
    if st.button("🔍 不足確認", type="primary", use_container_width=True):
        if not inventory_file:
            st.error("倉庫在庫ファイルをアップロードしてください。")
            return
        if not order_files:
            st.error("受注ファイルを1つ以上アップロードしてください。")
            return
        
        try:
            with st.spinner("データを解析中..."):
                # 倉庫在庫読み込み
                inventory_df = load_inventory_file(inventory_file)
                
                # 受注ファイル読み込み（複数対応）
                order_dfs = []
                for o_file in order_files:
                    if o_file.name.lower().endswith('.pdf'):
                        order_dfs.append(process_pdf_order(o_file))
                    else:
                        order_dfs.append(load_order_file(o_file))
                
                # 受注データの結合
                combined_order_df = pd.concat(order_dfs, ignore_index=True)
                
                # 引当計算
                allocation_df = calculate_allocation(inventory_df, combined_order_df)
                
            # 結果表示
            display_results(allocation_df, combined_order_df)
            
        except Exception as e:
            st.error(f"エラー: {str(e)}")
    
    # Documentation
    with st.expander("📖 システム仕様・使用方法"):
        st.markdown("""
        ### 🚀 概要
        このツールは、最新の倉庫在庫データと1つ以上の受注ファイルを照合し、在庫が不足している商品を即座に特定します。
        
        ### 📂 対応ファイル形式
        - **倉庫在庫**: `.xlsx`, `.csv` (保管場所 `A309001` が対象)
        - **受注ファイル**: `.txt` (タブ区切り形式, 複数ファイルの一括処理に対応)
        
        ### 🛠️ 自動処理プロセス
        1. **入庫予定加算**: `倉庫在庫数 + (入庫予定 × 入数)` で実質在庫を算出
        2. **不良在庫除外**: ロケーション（E列）が `9` で始まる在庫を引当対象から除外
        3. **特定商品除外**: 商品コード `30126` を自動的に除外
        4. **正規化**: 商品コードの先頭ゼロを自動削除し、突合精度を向上
        5. **一括集計**: 複数アップロードされた受注ファイル内の同一商品を自動で合算
        """)

if __name__ == "__main__":
    main()
