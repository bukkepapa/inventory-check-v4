import pandas as pd
from app import process_pdf_order, calculate_allocation, display_results
import os
import streamlit as st
import sys

# Mock streamlit for offline testing
class MockFile:
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
    def read(self):
        with open(self.path, 'rb') as f:
            return f.read()

def test_pdf_extraction():
    pdf_path = r"c:\Users\PC_User\Desktop\Antigravity\在庫引当チェックツール_vr3\PDF ファイル\受注一覧リスト必須項目.pdf"
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    print(f"Testing OCR extraction on: {pdf_path}")
    mock_file = MockFile(pdf_path)
    
    try:
        df = process_pdf_order(mock_file)
        print("\nExtracted DataFrame:")
        print(df)
        
        if not df.empty:
            print("\nRow 0 details:")
            print(df.iloc[0])
    except Exception as e:
        print(f"Error during extraction: {e}")

def test_special_handling():
    inventory_df = pd.DataFrame([
        {'商品コード': '19005', '倉庫在庫数': 0},
        {'商品コード': '100', '倉庫在庫数': 10}
    ])
    
    order_df = pd.DataFrame([
        {'商品コード': '19005', '発注数量': 5, '顧客コード': '123456789', '顧客名': 'Test Cust', '商品名漢字': 'Special Item', '商品名カナ': ''},
        {'商品コード': '100', '発注数量': 15, '顧客コード': '987654321', '顧客名': 'Normal Cust', '商品名漢字': 'Normal Item', '商品名カナ': ''}
    ])
    
    print("\nTesting Allocation Logic (including 0019005)...")
    allocation_df = calculate_allocation(inventory_df, order_df)
    
    print("\nAllocation Results:")
    print(allocation_df)
    
    # Check if 19005 has 引当後在庫 = 0 (as per my logic to ignore shortage)
    item_19005 = allocation_df[allocation_df['商品コード'] == '19005'].iloc[0]
    item_100 = allocation_df[allocation_df['商品コード'] == '100'].iloc[0]
    
    print(f"Item 19005 Index After Stock: {item_19005['引当後在庫']} (Expected 0)")
    print(f"Item 100 Index After Stock: {item_100['引当後在庫']} (Expected -5)")
    
    if item_19005['引当後在庫'] == 0:
        print("SUCCESS: 0019005 treated correctly.")
    else:
        print("FAILURE: 0019005 handling failed.")

if __name__ == "__main__":
    # We need to mock st.cache_resource
    def mock_cache(func):
        return func
    st.cache_resource = mock_cache
    
    test_pdf_extraction()
    test_special_handling()
