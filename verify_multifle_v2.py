import pandas as pd
from io import StringIO

# Mock functions from app.py (simplified)
def load_order_file_mock(content, name):
    df = pd.read_csv(
        StringIO(content),
        sep='\t',
        header=0,
        usecols=[14, 15, 97, 106, 108, 118]
    )
    df.columns = ['顧客コード', '顧客名', '商品コード', '商品名漢字', '商品名カナ', '発注数量']
    df['発注数量'] = pd.to_numeric(df['発注数量'], errors='coerce').fillna(0).astype(int)
    df['商品コード'] = df['商品コード'].astype(str).str.lstrip('0')
    return df

def calculate_allocation_mock(inventory_df, order_df):
    order_summary = order_df.groupby('商品コード').agg({
        '発注数量': 'sum',
        '商品名漢字': 'first',
        '商品名カナ': 'first'
    }).reset_index()
    order_summary.columns = ['商品コード', '受注合計数', '商品名漢字', '商品名カナ']
    order_summary['商品名'] = order_summary['商品名漢字'].fillna(order_summary['商品名カナ']).fillna('')
    order_summary = order_summary[['商品コード', '受注合計数', '商品名']]
    
    allocation_df = order_summary.merge(inventory_df, on='商品コード', how='left')
    allocation_df['倉庫在庫数'] = allocation_df['倉庫在庫数'].fillna(0).astype(int)
    allocation_df['引当後在庫'] = allocation_df['倉庫在庫数'] - allocation_df['受注合計数']
    
    return allocation_df

# Test Data
order1_content = """No\tC_Code\tC_Name\tP_Code\tP_NameK\tP_NameC\tQty
1\t1001\tCust A\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t101\tCust A\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t9\t900\tItem A\tItem A_K\t9\t9\t9\t9\t9\t9\t9\t9\t9\t10
"""
# Wait, the columns are 14, 15, 97, 106, 108, 118.
# Let's make a more realistic TSV string.

header = "\t".join([str(i) for i in range(120)])
row1_cols = ["v"] * 120
row1_cols[14] = "C001"
row1_cols[15] = "Customer A"
row1_cols[97] = "12345"
row1_cols[106] = "Product A"
row1_cols[108] = "プロダクトA"
row1_cols[118] = "10"
row1 = "\t".join(row1_cols)

row2_cols = ["v"] * 120
row2_cols[14] = "C002"
row2_cols[15] = "Customer B"
row2_cols[97] = "67890"
row2_cols[106] = "Product B"
row2_cols[108] = "プロダクトB"
row2_cols[118] = "5"
row2 = "\t".join(row2_cols)

order1_tsv = header + "\n" + row1 + "\n" + row2

row3_cols = ["v"] * 120
row3_cols[14] = "C001"
row3_cols[15] = "Customer A"
row3_cols[97] = "12345"
row3_cols[106] = "Product A"
row3_cols[108] = "プロダクトA"
row3_cols[118] = "7"
row3 = "\t".join(row3_cols)

order2_tsv = header + "\n" + row3

# Inventory Data
inventory_df = pd.DataFrame({
    '商品コード': ['12345', '67890'],
    '倉庫在庫数': [15, 10]
})

print("Testing multi-file order processing...")
df1 = load_order_file_mock(order1_tsv, "file1.txt")
df2 = load_order_file_mock(order2_tsv, "file2.txt")

combined_df = pd.concat([df1, df2], ignore_index=True)
print(f"Combined row count: {len(combined_df)} (Expected: 3)")

allocation = calculate_allocation_mock(inventory_df, combined_df)
print("\nAllocation Result:")
print(allocation)

# Check for Product 12345 (Total order: 10 + 7 = 17, Stock: 15, Shortage: -2)
prod_12345 = allocation[allocation['商品コード'] == '12345'].iloc[0]
print(f"\nProduct 12345 - Stock: {prod_12345['倉庫在庫数']}, Order: {prod_12345['受注合計数']}, After: {prod_12345['引当後在庫']}")

assert prod_12345['受注合計数'] == 17
assert prod_12345['引当後在庫'] == -2
print("\nMulti-file logic verification SUCCESSFUL!")
