import streamlit as st
import pandas as pd
import requests
import json
import time
import os

# === 認証情報（Render上では環境変数で設定） ===
shop_name = os.getenv("SHOPIFY_SHOP_NAME")  # 例: plumdesign.myshopify.com
access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
api_version = "2023-10"
url = f"https://{shop_name}/admin/api/{api_version}/products.json"
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": access_token
}

# === サイズ表HTMLを生成 ===
def generate_size_table_extended(row):
    sizes = ["S", "M", "L", "XL","XXL"]
    headers = shoulders = widths = lengths = sleeves = ""

    for size in sizes:
        if pd.notna(row.get(f"{size}サイズ肩幅", "")) and row[f"{size}サイズ肩幅"] != "":
            headers += f"<td style='padding:6px 12px;'>{size}</td>"
            shoulders += f"<td style='padding:6px 12px;'>{row.get(f'{size}サイズ肩幅', '')}</td>"
            widths += f"<td style='padding:6px 12px;'>{row.get(f'{size}サイズ身幅', '')}</td>"
            lengths += f"<td style='padding:6px 12px;'>{row.get(f'{size}サイズ着丈', '')}</td>"
            sleeves += f"<td style='padding:6px 12px;'>{row.get(f'{size}サイズ袖丈', '')}</td>"

    return f"""
    <p style='font-size:9pt;'>サイズ表：(CM)</p>
    <table style="border-collapse:collapse; font-size:9pt; line-height:2.2;">
      <tr><td style='padding:6px 12px;'></td>{headers}</tr>
      <tr><td style='padding:6px 12px;'>肩幅</td>{shoulders}</tr>
      <tr><td style='padding:6px 12px;'>身幅</td>{widths}</tr>
      <tr><td style='padding:6px 12px;'>着丈</td>{lengths}</tr>
      <tr><td style='padding:6px 12px;'>袖丈</td>{sleeves}</tr>
    </table>
    """

def format_sku(sku):
    sku = str(sku)
    return sku.replace("-", "")[:12]

# === Streamlit UI部分 ===
st.title("Shopify商品登録ツール")
uploaded_file = st.file_uploader("商品CSVファイルをアップロードしてください", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding="shift_jis")
        st.success("CSV読み込み成功！")
        st.dataframe(df.head())

        if st.button("Shopifyに商品を登録する"):
            grouped = df.groupby("Handle")
            success_count = 0

            for handle, group in grouped:
                first = group.iloc[0]
                size_table_html = generate_size_table_extended(first)
                formatted_sku = format_sku(first["Variant SKU"])
                colors = ", ".join(group["Option2 Value"].dropna().unique())
                fabric = "Polyester"

                body_html = f"""
                <div style="font-size: 9pt; line-height: 2;">
                    <p>SKU: {formatted_sku}<br>
                    Color: {colors}<br>
                    Fabric: {fabric}</p>
                    {size_table_html}
                </div>
                """

                variants = []
                for _, row in group.iterrows():
                    variant = {
                        "option1": row["Option1 Value"],
                        "option2": row["Option2 Value"],
                        "price": str(row["Variant Price"]),
                        "sku": row["Variant SKU"],
                        "inventory_quantity": int(row["Variant Inventory Qty"]),
                        "inventory_management": "shopify"
                    }
                    variants.append(variant)

                product_data = {
                    "product": {
                        "handle": first["Handle"],
                        "title": first["Title"],
                        "status": "draft",
                        "body_html": body_html,
                        "vendor": first["Vendor"],
                        "product_type": first["Product Type"],
                        "tags": first["Tags"],
                        "options": [
                            {"name": "サイズ"},
                            {"name": "色"}
                        ],
                        "variants": variants
                    }
                }

                response = requests.post(url, headers=headers, data=json.dumps(product_data))
                if response.status_code == 201:
                    st.success(f"✅ 登録成功: {first['Title']}")
                    success_count += 1
                else:
                    st.error(f"❌ 登録失敗: {first['Title']} → {response.status_code}: {response.text}")

                time.sleep(1)

            st.info(f"登録処理完了（成功：{success_count}件）")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
