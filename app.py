import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="台東分隊大補帖儀表板", layout="wide", initial_sidebar_state="expanded")

# 2. 自動產生的 Google 試算表 CSV 匯出連結
SHEET_ID = "1gi-0Lgy16kTp_S806AIivIUlC0m-_q9-uZPEZY5mLY4"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=300) 
def load_data():
    df = pd.read_csv(SHEET_URL)
    
    # --- 安全檢查：確保必要欄位存在，不存在就補空欄位 ---
    expected_cols = ['更新日期', '管理類別', '類別', '更新標題', '連結', '重要性(1-10)', '標籤(Tag)', '詳細內容']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = "" # 如果沒這欄位，就補一個空的，避免程式當機
            
    # 格式轉換
    df['更新日期'] = pd.to_datetime(df['更新日期'], errors='coerce')
    df = df.dropna(subset=['更新日期']) # 移除日期錯誤的列
    df['詳細內容'] = df['詳細內容'].fillna('')
    df['標籤(Tag)'] = df['標籤(Tag)'].fillna('無')
    df['連結'] = df['連結'].fillna('')
    df['重要性(1-10)'] = pd.to_numeric(df['重要性(1-10)'], errors='coerce').fillna(0)
    
    return df

def highlight_importance(row):
    val = row['重要性(1-10)']
    if val >= 9:
        return ['background-color: #ffcccc'] * len(row)
    elif val >= 7:
        return ['background-color: #fff3cd'] * len(row)
    else:
        return [''] * len(row)

try:
    df = load_data()

    # --- 側邊欄 ---
    st.sidebar.header("🔍 篩選控制台")
    search_query = st.sidebar.text_input("關鍵字搜尋", placeholder="搜尋標題、內容或標籤...")
    
    mgt_list = ["全部"] + sorted(list(df['管理類別'].astype(str).unique()))
    selected_mgt = st.sidebar.selectbox("管理類別 (大項)", mgt_list)
    
    if selected_mgt == "全部":
        sub_cats = sorted(df['類別'].astype(str).unique())
    else:
        sub_cats = sorted(df[df['管理類別'] == selected_mgt]['類別'].astype(str).unique())
    
    selected_sub = st.sidebar.multiselect("詳細類別篩選", sub_cats, default=sub_cats)

    # 過濾
    filtered_df = df[df['類別'].isin(selected_sub)]
    if search_query:
        mask = (
            filtered_df['更新標題'].astype(str).str.contains(search_query, case=False) |
            filtered_df['詳細內容'].astype(str).str.contains(search_query, case=False) |
            filtered_df['標籤(Tag)'].astype(str).str.contains(search_query, case=False)
        )
        filtered_df = filtered_df[mask]

    # --- 主頁面 ---
    st.title("🚒 台東分隊大補帖更新紀錄")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📚 總資料筆數", len(df))
    m2.metric("🎯 篩選結果", len(filtered_df))
    if not df.empty:
        m3.metric("📅 最近更新", df['更新日期'].max().strftime('%Y-%m-%d'))
    critical_count = len(df[df['重要性(1-10)'] >= 8])
    m4.metric("🚨 重大更新數", critical_count)

    st.divider()

    # 圖表
    c1, c2 = st.columns(2)
    with c1:
        fig_pie = px.pie(filtered_df, names='類別', title='各類別分佈', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        trend_df = filtered_df.resample('M', on='更新日期').size().reset_index(name='件數')
        fig_bar = px.bar(trend_df, x='更新日期', y='件數', title='每月更新趨勢')
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- 表格顯示 ---
    st.subheader("📋 詳細紀錄清單")
    
    display_cols = ['更新日期', '管理類別', '類別', '更新標題', '連結', '重要性(1-10)', '標籤(Tag)', '詳細內容']
    # 只顯示試算表中「真的有」的欄位
    actual_display_cols = [c for c in display_cols if c in filtered_df.columns]
    
    display_df = filtered_df[actual_display_cols].sort_values(by='更新日期', ascending=False)
    display_df['更新日期'] = display_df['更新日期'].dt.strftime('%Y-%m-%d')
    
    st.dataframe(
        display_df.style.apply(highlight_importance, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "連結": st.column_config.LinkColumn("相關連結", display_text="🔗 開啟連結"),
            "重要性(1-10)": st.column_config.NumberColumn("重要性", format="%d ⭐"),
            "詳細內容": st.column_config.TextColumn("詳細內容", width="large")
        }
    )

except Exception as e:
    st.error(f"⚠️ 資料讀取失敗，請確認試算表權限已設為『知道連結的任何人皆可檢視』。")
    st.info(f"技術訊息: {e}")
