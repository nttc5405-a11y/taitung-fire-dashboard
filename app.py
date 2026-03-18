import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. 網頁基本設定：支援行動端寬度調整
st.set_page_config(
    page_title="台東分隊大補帖管理系統",
    page_icon="🚒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 資料讀取 (連結你的 Google 試算表)
SHEET_ID = "1gi-0Lgy16kTp_S806AIivIUlC0m-_q9-uZPEZY5mLY4"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(SHEET_URL)
    # 確保必要欄位存在
    expected_cols = ['更新日期', '管理類別', '類別', '更新標題', '連結', '重要性(1-10)', '標籤(Tag)', '詳細內容']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
            
    df['更新日期'] = pd.to_datetime(df['更新日期'], errors='coerce')
    df = df.dropna(subset=['更新日期'])
    df['重要性(1-10)'] = pd.to_numeric(df['重要性(1-10)'], errors='coerce').fillna(0)
    df = df.sort_values('更新日期', ascending=False)
    return df

# 3. 樣式美化函數
def highlight_importance(row):
    val = row['重要性(1-10)']
    if val >= 9: return ['background-color: #ffcccc'] * len(row)
    if val >= 7: return ['background-color: #fff3cd'] * len(row)
    return [''] * len(row)

try:
    df = load_data()
    today = datetime.now()

    # --- 側邊欄：過濾控制 ---
    st.sidebar.header("🚒 知識庫篩選")
    
    # 功能 A：快選按鈕 (Streamlit Pills)
    st.sidebar.subheader("快速查看")
    quick_filter = st.sidebar.radio("時間區間", ["全部", "最近 7 天", "最近 30 天"], horizontal=True)
    
    # 功能 B：關鍵字搜尋
    search_query = st.sidebar.text_input("🔍 關鍵字搜尋", placeholder="搜尋標題、內容或標籤...")
    
    # 功能 C：分類過濾
    mgt_list = ["全部"] + sorted(list(df['管理類別'].astype(str).unique()))
    selected_mgt = st.sidebar.selectbox("管理類別 (大項)", mgt_list)
    
    sub_cats = df['類別'].unique() if selected_mgt == "全部" else df[df['管理類別'] == selected_mgt]['類別'].unique()
    selected_sub = st.sidebar.multiselect("詳細類別", sorted(list(sub_cats)), default=list(sub_cats))

    # --- 資料過濾邏輯 ---
    f_df = df[df['類別'].isin(selected_sub)]
    if quick_filter == "最近 7 天":
        f_df = f_df[f_df['更新日期'] >= (today - timedelta(days=7))]
    elif quick_filter == "最近 30 天":
        f_df = f_df[f_df['更新日期'] >= (today - timedelta(days=30))]
        
    if search_query:
        f_df = f_df[f_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

    # --- 主頁面佈局 ---
    st.title("🚒 台東分隊大補帖更新紀錄")

    # A. 數據速報 (含 Delta 指標)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📚 總資料筆數", len(df))
    
    # 計算本月與上月更新數以顯示增長
    this_month_count = len(df[df['更新日期'].dt.month == today.month])
    last_month_count = len(df[df['更新日期'].dt.month == (today.month - 1 if today.month > 1 else 12)])
    m2.metric("🎯 本月更新", f"{this_month_count} 筆", delta=f"{this_month_count - last_month_count}")
    
    m3.metric("🚨 重大更新", len(df[df['重要性(1-10)'] >= 9]))
    m4.metric("📅 篩選結果", len(f_df))

    # B. 重大公告欄 (針對重要性 10 的項目)
    urgent_news = df[df['重要性(1-10)'] == 10].head(1)
    if not urgent_news.empty:
        st.error(f"🚨 **重大更新公告：** {urgent_news.iloc[0]['更新標題']} ({urgent_news.iloc[0]['更新日期'].strftime('%Y-%m-%d')})")

    st.divider()

    # C. 視覺化圖表 (行動端並排優化)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        # 改用水平長條圖，文字更清晰
        cat_counts = f_df['類別'].value_counts().reset_index()
        fig_cat = px.bar(cat_counts, x='count', y='index', orientation='h', title='業務領域分佈',
                         labels={'count':'筆數', 'index':'類別'}, color='count', color_continuous_scale='Reds')
        fig_cat.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_cat, use_container_width=True)
    
    with c2:
        # 月份趨勢圖
        trend_df = f_df.resample('M', on='更新日期').size().reset_index(name='件數')
        fig_trend = px.line(trend_df, x='更新日期', y='件數', title='每月產出趨勢', markers=True)
        fig_trend.update_traces(line_color='#FF4B4B')
        fig_trend.update_layout(height=350)
        st.plotly_chart(fig_trend, use_container_width=True)

    # D. 資料表格與匯出功能
    st.subheader("📋 紀錄清單")
    
    col_tab1, col_tab2 = st.columns([8, 2])
    with col_tab2:
        # 增加匯出 CSV 功能
        csv = f_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 匯出報表", data=csv, file_name=f"大補帖更新_{today.strftime('%Y%m%d')}.csv", mime='text/csv')

    # 設定顯示欄位
    display_cols = ['更新日期', '管理類別', '類別', '更新標題', '連結', '重要性(1-10)', '標籤(Tag)']
    # 日期顯示轉換為字串避免表格顯示時間戳
    plot_df = f_df[display_cols].copy()
    plot_df['更新日期'] = plot_df['更新日期'].dt.strftime('%Y-%m-%d')

    st.dataframe(
        plot_df.style.apply(highlight_importance, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "連結": st.column_config.LinkColumn("相關連結", display_text="🔗 開啟"),
            "重要性(1-10)": st.column_config.NumberColumn("重要性", format="%d ⭐"),
            "更新標題": st.column_config.TextColumn("標題", width="medium")
        }
    )

    # E. 詳細內容收折區 (精進點：不佔用表格空間)
    st.markdown("---")
    st.subheader("📝 內容深挖 (Deep Dive)")
    selected_title = st.selectbox("請選擇要查看詳細內容的標題：", ["請選擇..."] + list(f_df['更新標題']))
    
    if selected_title != "請選擇...":
        detail_row = f_df[f_df['更新標題'] == selected_title].iloc[0]
        with st.expander(f"查看【{selected_title}】的詳細資訊", expanded=True):
            st.write(f"**更新日期：** {detail_row['更新日期'].strftime('%Y-%m-%d')}")
            st.write(f"**詳細內容：**")
            st.info(detail_row['詳細內容'] if detail_row['詳細內容'] else "暫無詳細內容說明。")
            if detail_row['標籤(Tag)']:
                st.write(f"**標籤：** `{detail_row['標籤(Tag)']}`")

except Exception as e:
    st.error(f"系統運行中發生錯誤：{e}")
