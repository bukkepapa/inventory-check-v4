import streamlit as st
import pandas as pd
from io import BytesIO


def load_inventory_file(file):
    """
    速報倉庫在庫ファイルを読み込む
    
    Args:
        file: アップロードされたファイルオブジェクト
    
    Returns:
        DataFrame: 商品コードと倉庫在庫数を含むDataFrame
    """
    try:
        # ファイル拡張子で判別
        file_ext = file.name.split('.')[-1].lower()
        
        if file_ext == 'csv':
            # CSV形式で読み込み（ヘッダーなし、B列=1(保管場所), I列=8(品目コード), N列=13(在庫数)）
            # WindowsのCSVはCP932(Shift_JIS拡張)が多い
            df = pd.read_csv(file, header=None, usecols=[1, 8, 13], encoding='cp932')
            # 列名を設定
            df.columns = ['保管場所', '商品コード', '倉庫在庫数']
            
            # 保管場所が 'A309001' のデータのみ抽出
            df = df[df['保管場所'] == 'A309001']
            
        elif file_ext in ['xlsx', 'xls']:
            # Excel形式の場合も同様の構造（B, I, N列）と仮定、ただしヘッダーがあるか不明なため
            # ユーザー指示のCSV構造に合わせる形で実装（既存のExcelロジックはコメントアウトまたは置換）
            # 今回はCSVが添付されているためCSVロジックをExcelにも適用（ヘッダーなしと仮定するか、ヘッダーありと仮定するかリスクだが一旦ヘッダーなしで読む）
            df = pd.read_excel(file, header=None, usecols=[1, 8, 13])
            df.columns = ['保管場所', '商品コード', '倉庫在庫数']
            df = df[df['保管場所'] == 'A309001']
        else:
            raise ValueError(f"サポートされていないファイル形式です: {file_ext}")
        
        # 倉庫在庫数を整数型に変換（変換失敗時は0）
        df['倉庫在庫数'] = pd.to_numeric(df['倉庫在庫数'], errors='coerce').fillna(0).astype(int)
        
        # 商品コードの欠損値を除外
        df = df.dropna(subset=['商品コード'])
        
        # 商品コードを文字列型に変換（マージ時のデータ型一致のため）
        # 先頭のゼロを削除して正規化（マッピング不一致防止）
        df['商品コード'] = df['商品コード'].astype(str).str.lstrip('0')
        
        # 不要な保管場所列を削除し、必要な列だけ返す
        return df[['商品コード', '倉庫在庫数']]
    
    except Exception as e:
        raise Exception(f"倉庫在庫ファイルの読み込みエラー: {str(e)}")


def load_order_file(file):
    """
    受注ファイルを読み込む
    
    Args:
        file: アップロードされたファイルオブジェクト
    
    Returns:
        DataFrame: 顧客コード、顧客名、商品コード、発注数量を含むDataFrame
    """
    try:
        # Shift-JIS、タブ区切りで読み込み
        # 必要な列のみ指定: 14=顧客コード, 15=顧客名, 97=商品コード, 106=商品名（漢字）, 108=商品名（カナ）, 118=発注数量
        df = pd.read_csv(
            file,
            encoding='shift_jis',
            sep='\t',
            header=0,
            usecols=[14, 15, 97, 106, 108, 118]
        )
        
        # 列名を設定
        df.columns = ['顧客コード', '顧客名', '商品コード', '商品名漢字', '商品名カナ', '発注数量']
        
        # 発注数量を整数型に変換（変換失敗時は0）
        df['発注数量'] = pd.to_numeric(df['発注数量'], errors='coerce').fillna(0).astype(int)
        
        # 商品コードの欠損値を除外
        df = df.dropna(subset=['商品コード'])
        
        # 商品コードを文字列型に変換（マージ時のデータ型一致のため）
        # 先頭のゼロを削除して正規化
        df['商品コード'] = df['商品コード'].astype(str).str.lstrip('0')
        
        # 商品コード30126を除外（システム仕様）
        df = df[df['商品コード'] != '30126']
        
        return df
    
    except UnicodeDecodeError:
        raise Exception("受注ファイルの文字コードエラー: Shift-JISでの読み込みに失敗しました。ファイルのエンコーディングを確認してください。")
    except Exception as e:
        raise Exception(f"受注ファイルの読み込みエラー: {str(e)}")


def calculate_allocation(inventory_df, order_df):
    """
    在庫引当を計算する
    
    Args:
        inventory_df: 倉庫在庫DataFrame
        order_df: 受注DataFrame
    
    Returns:
        DataFrame: 引当計算結果を含むDataFrame
    """
    # 商品コードごとに発注数量を集計（商品名も保持するため、firstを使用）
    # 注意: 商品コードでグループ化し、発注数量はsum、商品名はfirst（代表値）を取得
    order_summary = order_df.groupby('商品コード').agg({
        '発注数量': 'sum',
        '商品名漢字': 'first',
        '商品名カナ': 'first'
    }).reset_index()
    order_summary.columns = ['商品コード', '受注合計数', '商品名漢字', '商品名カナ']
    
    # 商品名（漢字）が欠損している場合、商品名（カナ）を使用
    order_summary['商品名'] = order_summary['商品名漢字'].fillna(order_summary['商品名カナ']).fillna('')
    
    # 不要な列を削除
    order_summary = order_summary[['商品コード', '受注合計数', '商品名']]
    
    # 商品コードを文字列型に変換（念のため）
    order_summary['商品コード'] = order_summary['商品コード'].astype(str)
    
    # 受注ベースで倉庫在庫とマージ（受注がある商品のみチェック）
    allocation_df = order_summary.merge(inventory_df, on='商品コード', how='left')
    
    # 倉庫在庫がない商品は在庫数0とする
    allocation_df['倉庫在庫数'] = allocation_df['倉庫在庫数'].fillna(0).astype(int)
    
    # 引当後在庫を計算
    allocation_df['引当後在庫'] = allocation_df['倉庫在庫数'] - allocation_df['受注合計数']
    
    return allocation_df


def display_results(allocation_df, order_df):
    """
    結果を表示する
    
    Args:
        allocation_df: 引当計算結果DataFrame
        order_df: 受注DataFrame（顧客情報取得用）
    """
    # 不足商品を抽出
    shortage_df = allocation_df[allocation_df['引当後在庫'] < 0].copy()
    
    if shortage_df.empty:
        # 全商品在庫アリ
        st.success("✅ 全商品在庫アリ")
    else:
        # 不足商品アリ
        st.error("⚠️ 不足商品アリ")
        
        # 不足数を計算（絶対値）
        shortage_df['不足数'] = shortage_df['引当後在庫'].abs()
        
        # 各不足商品について、顧客情報を集約
        customer_info = []
        for _, row in shortage_df.iterrows():
            product_code = row['商品コード']
            product_name = row['商品名']  # allocation_dfから直接取得
            
            # この商品を注文した顧客を抽出
            customers = order_df[order_df['商品コード'] == product_code][['顧客コード', '顧客名']].drop_duplicates()
            
            # 顧客コードと顧客名をリスト化
            customer_codes = ', '.join(customers['顧客コード'].astype(str).tolist())
            customer_names = ', '.join(customers['顧客名'].astype(str).tolist())
            
            customer_info.append({
                '商品コード': product_code,
                '商品名': product_name,
                '倉庫在庫数': row['倉庫在庫数'],
                '受注合計数': row['受注合計数'],
                '不足数': row['不足数'],
                '顧客コード': customer_codes,
                '顧客名': customer_names
            })
        
        # 結果をDataFrameに変換して表示
        result_df = pd.DataFrame(customer_info)
        
        st.subheader("不足商品リスト")
        st.dataframe(result_df, use_container_width=True)


def main():
    """メインアプリケーション"""
    st.set_page_config(
        page_title="在庫引当チェックツール",
        page_icon="📦",
        layout="wide"
    )
    
    st.title("📦 在庫引当チェックツール")
    st.markdown("---")
    
    # ファイルアップロードセクション
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("① 速報倉庫在庫ファイル")
        inventory_file = st.file_uploader(
            "Excel または CSV ファイルをアップロード",
            type=['xlsx', 'xls', 'csv'],
            key='inventory'
        )
    
    with col2:
        st.subheader("② 受注ファイル")
        order_file = st.file_uploader(
            "テキストファイルをアップロード",
            type=['txt'],
            key='order'
        )
    
    st.markdown("---")
    
    # 実行ボタン
    if st.button("🔍 在庫引当チェック実行", type="primary", use_container_width=True):
        # ファイルがアップロードされているか確認
        if inventory_file is None or order_file is None:
            st.error("⚠️ 両方のファイルをアップロードしてください。")
            return
        
        try:
            with st.spinner("ファイルを読み込み中..."):
                # ファイル読み込み
                inventory_df = load_inventory_file(inventory_file)
                order_df = load_order_file(order_file)
            
            with st.spinner("在庫引当を計算中..."):
                # 引当計算
                allocation_df = calculate_allocation(inventory_df, order_df)
            
            # 結果表示
            st.markdown("---")
            st.subheader("📊 チェック結果")
            display_results(allocation_df, order_df)
            
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")
    
    # 使用方法の説明
    with st.expander("📖 使用方法"):
        st.markdown("""
        ### ファイル形式の要件
        
        **① 速報倉庫在庫ファイル (.xlsx, .csv)**
        - ヘッダー: 4行目
        - C列: 商品コード
        - E列: 倉庫在庫数
        
        **② 受注ファイル (.txt)**
        - 文字コード: Shift-JIS
        - 区切り文字: タブ
        - 列インデックス:
          - 14: 顧客コード
          - 15: 顧客名
          - 97: 商品コード
          - 118: 発注数量
        
        ### 実行手順
        1. 両方のファイルをアップロード
        2. 「在庫引当チェック実行」ボタンをクリック
        3. 結果を確認
        
        ### 結果の見方
        - **全商品在庫アリ**: すべての商品で在庫が十分にあります
        - **不足商品アリ**: 在庫不足の商品があります。不足商品リストで詳細を確認してください
        
        ### 注意事項
        - 商品コード30126は自動的に除外されます
        - 受注ファイルに含まれる商品のみチェック対象となります
        """)


if __name__ == "__main__":
    main()
