import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="台東分隊大補帖儀表板", layout="wide", initial_sidebar_state="expanded")

# 2. 自動產生的 Google 試算表 CSV 匯出連結
SHEET_ID = "1gi-0Lgy16kTp_S806AIivIUlC0m-_q9-uZPEZY5mLY4"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=300) # 每 5 分鐘自動刷新
def load_data():
    df = pd.read_csv(SHEET_URL)
    df['更新日期'] = pd.to_datetime(df['更新日期'])
    df['詳細內容'] = df['詳細內容'].fillna('')
    df['標籤(Tag)'] = df['標籤(Tag)'].fillna('無')
    df['連結'] = df['連結'].fillna('')
    df['重要性(1-10)'] = pd.to_numeric(df['重要性(1-10)'], errors='coerce').fillna(0)
    return df

# 3. 樣式定義：根據重要性顯示顏色
def highlight_importance(row):
    val = row['重要性(1-10)']
    if val >= 9:
        return ['background-color: #ffcccc'] * len(row) # 核心更新：淡紅色
    elif val >= 7:
        return ['background-color: #fff3cd'] * len(row) # 重要提醒：淡黃色
    else:
        return [''] * len(row)

try:
    df = load_data()

    # --- 側邊欄控制 ---
    st.sidebar.header("🔍 篩選與搜尋")
    search_query = st.sidebar.text_input("關鍵字搜尋", placeholder="例如: 射水, 救護, MSA...")
    
    mgt_list = ["全部"] + sorted(list(df['管理類別'].dropna().unique()))
    selected_mgt = st.sidebar.selectbox("管理類別 (大項)", mgt_list)
    
    if selected_mgt == "全部":
        available_sub_cats = sorted(df['類別'].dropna().unique())
    else:
        available_sub_cats = sorted(df[df['管理類別'] == selected_mgt]['類別'].dropna().unique())
    
    selected_sub = st.sidebar.multiselect("詳細類別篩選", available_sub_cats, default=available_sub_cats)

    # 過濾邏輯
    filtered_df = df[df['類別'].isin(selected_sub)]
    if search_query:
        mask = (
            filtered_df['更新標題'].str.contains(search_query, case=False, na=False) |
            filtered_df['詳細內容'].str.contains(search_query, case=False, na=False) |
            filtered_df['標籤(Tag)'].astype(str).str.contains(search_query, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    # --- 主頁面 ---
    st.title("🚒 台東分隊大補帖更新紀錄")
    
    # 頂部指標
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📚 總資料筆數", len(df))
    m2.metric("🎯 篩選結果", len(filtered_df))
    m3.metric("📅 最近更新", df['更新日期'].max().strftime('%Y-%m-%d'))
    critical_count = len(df[df['重要性(1-10)'] >= 8])
    m4.metric("🚨 重大更新數", critical_count)

    st.divider()

    # 圖表區
    c1, c2 = st.columns([1, 1])
    with c1:
        fig_pie = px.pie(filtered_df, names='類別', title='類別比例', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        trend_df = filtered_df.resample('M', on='更新日期').size().reset_index(name='件數')
        fig_trend = px.bar(trend_df, x='更新日期', y='件數', title='每月更新頻率')
        st.plotly_chart(fig_trend, use_container_width=True)

    # --- 重點：優化後的資料表格 ---
    st.subheader("📋 詳細紀錄清單")
    st.info("💡 提示：點擊「相關連結」欄位中的 **🔗 開啟** 即可查看詳細內容。")
    
    # 整理顯示順序
    display_cols = ['更新日期', '管理類別', '類別', '更新標題', '連結', '重要性(1-10)', '標籤(Tag)', '詳細內容']
    display_df = filtered_df[display_cols].sort_values(by='更新日期', ascending=False)
    
    # 格式化日期顯示
    display_df['更新日期'] = display_df['更新日期'].dt.strftime('%Y-%m-%d')
    
    # 使用 st.dataframe 的新功能 column_config
    st.dataframe(
        display_df.style.apply(highlight_importance, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "連結": st.column_config.LinkColumn(
                "相關連結",
                display_text="🔗 開啟連結" # 這樣網址就不會長長一串，而是整齊的文字
            ),
            "重要性(1-10)": st.column_config.NumberColumn(
                "重要性",
                format="%d ⭐"
            ),
            "詳細內容": st.column_config.TextColumn(
                "詳細內容",
                width="large" # 讓內容欄位寬一點，方便閱讀
            )
        }
    )

except Exception as e:
    st.error(f"⚠️ 資料讀取失敗，請確認試算表權限已設為『知道連結的任何人皆可檢視』。")
    st.info(f"技術訊息: {e}")
