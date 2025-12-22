import streamlit as st
import pandas as pd
from io import BytesIO
import base64

# --- UI Custom Styling ---
def apply_custom_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;700&display=swap');

        :root {
            --primary-color: #2563eb;
            --primary-hover: #1d4ed8;
            --bg-gradient: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            --card-bg: rgba(255, 255, 255, 0.9);
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }

        .stApp {
            background: var(--bg-gradient);
            font-family: 'Inter', 'Noto Sans JP', sans-serif;
            color: var(--text-main);
        }

        /* Header Styling */
        .main-header {
            background: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: var(--shadow-md);
            margin-bottom: 2rem;
            text-align: center;
            border: 1px solid var(--border-color);
        }

        .main-header h1 {
            color: var(--primary-color);
            font-weight: 700;
            margin-bottom: 0.5rem;
            font-size: 2.5rem;
        }

        .main-header p {
            color: var(--text-muted);
            font-size: 1.1rem;
        }

        /* Card-like containers for uploaders */
        .upload-card {
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 1rem;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
            height: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .upload-card:hover {
            box-shadow: var(--shadow-md);
        }

        .upload-title {
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 1.2rem;
        }

        /* Button Styling */
        .stButton > button {
            background: var(--primary-color) !important;
            color: white !important;
            border: none !important;
            padding: 0.75rem 2rem !important;
            border-radius: 0.75rem !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
            width: 100% !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: var(--shadow-md) !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .stButton > button:hover {
            background: var(--primary-hover) !important;
            transform: translateY(-2px) !important;
            box-shadow: var(--shadow-lg) !important;
        }

        /* Subheader Styling */
        .section-title {
            font-weight: 700;
            color: var(--text-main);
            margin-top: 2rem;
            margin-bottom: 1rem;
            border-left: 5px solid var(--primary-color);
            padding-left: 1rem;
        }

        /* Dataframe styling */
        .stDataFrame {
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }

        /* Success/Error Styling */
        .stAlert {
            border-radius: 0.75rem !important;
            border: none !important;
            box-shadow: var(--shadow-sm) !important;
        }

        /* Expander */
        .stExpander {
            background: white !important;
            border-radius: 0.75rem !important;
            border: 1px solid var(--border-color) !important;
            box-shadow: var(--shadow-sm) !important;
        }

        /* Hide Streamlit elements - REMOVED to show Deploy button */
        /* #MainMenu {visibility: hidden;} */
        /* footer {visibility: hidden;} */
        /* header {visibility: hidden;} */
        </style>
    """, unsafe_allow_html=True)

def load_inventory_file(file):
    """速報倉庫在庫ファイルを読み込む"""
    try:
        file_ext = file.name.split('.')[-1].lower()
        if file_ext == 'csv':
            df = pd.read_csv(file, header=None, usecols=[1, 8, 10, 13, 22], encoding='cp932')
            df.columns = ['保管場所', '商品コード', '入数', '倉庫在庫数', '入庫予定']
            df = df[df['保管場所'] == 'A309001']
        elif file_ext in ['xlsx', 'xls']:
            df = pd.read_excel(file, header=None, usecols=[1, 8, 10, 13, 22])
            df.columns = ['保管場所', '商品コード', '入数', '倉庫在庫数', '入庫予定']
            df = df[df['保管場所'] == 'A309001']
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
                usecols=[14, 15, 97, 106, 108, 118]
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
        df.columns = ['顧客コード', '顧客名', '商品コード', '商品名漢字', '商品名カナ', '発注数量']
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
    allocation_df['引当後在庫'] = allocation_df['倉庫在庫数'] - allocation_df['受注合計数']
    
    return allocation_df

def display_results(allocation_df, order_df):
    """結果を表示する"""
    shortage_df = allocation_df[allocation_df['引当後在庫'] < 0].copy()
    
    if shortage_df.empty:
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
        customer_info = []
        for _, row in shortage_df.iterrows():
            product_code = row['商品コード']
            customers = order_df[order_df['商品コード'] == product_code][['顧客コード', '顧客名']].drop_duplicates()
            customer_codes = ', '.join(customers['顧客コード'].astype(str).tolist())
            customer_names = ', '.join(customers['顧客名'].astype(str).tolist())
            
            customer_info.append({
                '商品コード': product_code,
                '商品名': row['商品名'],
                '倉庫在庫': row['倉庫在庫数'],
                '受注合計': row['受注合計数'],
                '不足数': row['不足数'],
                '該当顧客コード': customer_codes,
                '該当顧客名': customer_names
            })
        
        result_df = pd.DataFrame(customer_info)
        st.dataframe(result_df, use_container_width=True)

def main():
    st.set_page_config(
        page_title="在庫引当チェックツール | Smart Allocation",
        page_icon="📦",
        layout="wide"
    )
    
    apply_custom_style()
    
    # Header Section
    st.markdown("""
        <div class="main-header">
            <h1>📦 Smart Allocation</h1>
            <p>在庫引当チェックツール - 業務効率化のための洗練された在庫管理ソリューション</p>
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
            <div class="upload-title">📝 受注ファイル (複数可)</div>
        """, unsafe_allow_html=True)
        order_files = st.file_uploader(
            "テキストファイルを選択",
            type=['txt'],
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
        2. **特定商品除外**: 商品コード `30126` を自動的に除外
        3. **正規化**: 商品コードの先頭ゼロを自動削除し、突合精度を向上
        4. **一括集計**: 複数アップロードされた受注ファイル内の同一商品を自動で合算
        """)

if __name__ == "__main__":
    main()
