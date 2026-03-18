import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 頁面設定
st.set_page_config(page_title="台東分隊大補帖儀表板", layout="wide")

# 2. 設定 Google 試算表 CSV 匯出連結
# 請將下方的 URL 替換成你自己的「知道連結的任何人都能檢視」的試算表連結
# 記得網址結尾要改成 /export?format=csv
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gi-0Lgy16kTp_S806AIivIUlC0m-_q9-uZPEZY5mLY4/export?format=csv"

@st.cache_data(ttl=600)  # 每 10 分鐘快取自動失效，確保資料會更新
def load_data():
    # 讀取雲端資料
    df = pd.read_csv(SHEET_URL)
    # 強制轉換日期格式
    df['更新日期'] = pd.to_datetime(df['更新日期'])
    return df

try:
    df = load_data()

    # --- 介面開始 ---
    st.title("🚒 台東分隊大補帖 - 互動更新紀錄")
    
    # 頂部統計指標
    c1, c2, c3 = st.columns(3)
    c1.metric("📚 總資料筆數", len(df))
    c2.metric("🔥 最常更新領域", df['類別'].mode()[0])
    c3.metric("📅 最近更新", df['更新日期'].max().strftime('%Y/%m/%d'))

    st.divider()

    # 側邊欄：搜尋與過濾
    st.sidebar.header("🔍 快速檢索")
    search_text = st.sidebar.text_input("輸入關鍵字 (如: MSA, 救護)", "")
    
    all_categories = df['類別'].unique().tolist()
    selected_cats = st.sidebar.multiselect("過濾類別", all_categories, default=all_categories)

    # 過濾邏輯
    filtered_df = df[df['類別'].isin(selected_cats)]
    if search_text:
        filtered_df = filtered_df[
            filtered_df['更新標題'].str.contains(search_text, case=False, na=False) |
            filtered_df['詳細內容'].str.contains(search_text, case=False, na=False)
        ]

    # 圖表區
    col_left, col_right = st.columns(2)
    with col_left:
        fig_pie = px.pie(filtered_df, names='類別', title='各項業務比例', hole=0.5)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_right:
        # 依照月份統計更新頻率
        trend_data = filtered_df.resample('M', on='更新日期').size().reset_index(name='更新次數')
        fig_bar = px.bar(trend_data, x='更新日期', y='更新次數', title='月份更新趨勢')
        st.plotly_chart(fig_bar, use_container_width=True)

    # 資料表格
    st.subheader("📋 詳細紀錄清單")
    st.dataframe(
        filtered_df.sort_values('更新日期', ascending=False), 
        use_container_width=True, 
        hide_index=True
    )

except Exception as e:
    st.warning("請確認試算表連結是否已開啟權限，並確認欄位名稱正確。")
    st.error(f"錯誤訊息: {e}")
