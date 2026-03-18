import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="台東分隊大補帖儀表板", layout="wide", initial_sidebar_state="expanded")

# 2. 自動產生的 Google 試算表 CSV 匯出連結
SHEET_ID = "1gi-0Lgy16kTp_S806AIivIUlC0m-_q9-uZPEZY5mLY4"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=600) # 每 10 分鐘自動刷新一次資料
def load_data():
    # 讀取雲端資料
    df = pd.read_csv(SHEET_URL)
    
    # 欄位清理與轉換
    df['更新日期'] = pd.to_datetime(df['更新日期'])
    df['詳細內容'] = df['詳細內容'].fillna('')
    df['標籤(Tag)'] = df['標籤(Tag)'].fillna('無')
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

    # --- 側邊欄：搜尋與過濾控制 ---
    st.sidebar.header("🔍 儀表板控制台")
    
    # 關鍵字搜尋
    search_query = st.sidebar.text_input("搜尋關鍵字 (標題/內容/標籤)", placeholder="例如: 射水, 救護, MSA...")
    
    # 管理類別篩選 (大項)
    mgt_list = ["全部"] + sorted(list(df['管理類別'].dropna().unique()))
    selected_mgt = st.sidebar.selectbox("管理類別 (大項)", mgt_list)
    
    # 類別篩選 (細項)
    if selected_mgt == "全部":
        available_sub_cats = sorted(df['類別'].dropna().unique())
    else:
        available_sub_cats = sorted(df[df['管理類別'] == selected_mgt]['類別'].dropna().unique())
    
    selected_sub = st.sidebar.multiselect("詳細類別篩選", available_sub_cats, default=available_sub_cats)

    # 執行過濾邏輯
    filtered_df = df[df['類別'].isin(selected_sub)]
    if search_query:
        mask = (
            filtered_df['更新標題'].str.contains(search_query, case=False, na=False) |
            filtered_df['詳細內容'].str.contains(search_query, case=False, na=False) |
            filtered_df['標籤(Tag)'].astype(str).str.contains(search_query, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    # --- 主頁面視覺化 ---
    st.title("🚒 台東分隊大補帖更新紀錄")
    st.caption(f"數據自動同步中 (最後抓取時間：{datetime.now().strftime('%H:%M:%S')})")

    # A. 數據速報指標
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📚 總資料筆數", len(df))
    m2.metric("🎯 篩選結果", len(filtered_df))
    m3.metric("📅 最近更新", df['更新日期'].max().strftime('%Y-%m-%d'))
    # 重要更新數 (8分以上)
    critical_count = len(df[df['重要性(1-10)'] >= 8])
    m4.metric("🚨 重大更新數", critical_count)

    st.divider()

    # B. 圖表分析區
    c1, c2 = st.columns([1, 1])
    with c1:
        # 類別佔比圓餅圖
        fig_pie = px.pie(filtered_df, names='類別', title='當前類別佔比分佈', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with c2:
        # 月份更新趨勢
        trend_df = filtered_df.resample('M', on='更新日期').size().reset_index(name='件數')
        fig_trend = px.bar(trend_df, x='更新日期', y='件數', title='每月更新頻率趨勢',
                           labels={'更新日期': '時間', '件數': '更新件數'})
        st.plotly_chart(fig_trend, use_container_width=True)

    # C. 詳細紀錄清單 (含條件顏色)
    st.subheader("📋 詳細紀錄清單")
    st.info("💡 提示：紅色代表**極重要 (9分以上)**；黃色代表**重要 (7分以上)**。可點擊各欄位進行排序。")
    
    # 整理表格欄位順序
    display_cols = ['更新日期', '管理類別', '類別', '更新標題', '重要性(1-10)', '標籤(Tag)', '詳細內容']
    display_df = filtered_df[display_cols].sort_values(by='更新日期', ascending=False)
    
    # 日期顯示美化
    display_df['更新日期'] = display_df['更新日期'].dt.strftime('%Y-%m-%d')
    
    # 套用樣式
    styled_table = display_df.style.apply(highlight_importance, axis=1)
    
    st.dataframe(styled_table, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"⚠️ 資料連接失敗，請檢查試算表權限。")
    st.info(f"技術錯誤訊息: {e}")
