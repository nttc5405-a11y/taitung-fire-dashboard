import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. 網頁基本設定：支援行動端寬度調整與深色模式適配
st.set_page_config(
    page_title="台東分隊大補帖管理系統",
    page_icon="🚒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 自動產生的 Google 試算表 CSV 匯出連結
SHEET_ID = "1gi-0Lgy16kTp_S806AIivIUlC0m-_q9-uZPEZY5mLY4"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=300) # 每 5 分鐘自動刷新資料
def load_data():
    df = pd.read_csv(SHEET_URL)
    
    # --- 安全檢查：確保必要欄位存在，若缺失則自動補空，避免 KeyError ---
    expected_cols = ['更新日期', '管理類別', '類別', '更新標題', '連結', '重要性(1-10)', '標籤(Tag)', '詳細內容']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = "" # 若試算表內沒這欄，自動補空值
            
    # 格式清理
    df['更新日期'] = pd.to_datetime(df['更新日期'], errors='coerce')
    df = df.dropna(subset=['更新日期']) # 移除日期格式錯誤的列
    df['重要性(1-10)'] = pd.to_numeric(df['重要性(1-10)'], errors='coerce').fillna(0)
    df['詳細內容'] = df['詳細內容'].fillna('暫無詳細說明')
    df['標籤(Tag)'] = df['標籤(Tag)'].fillna('無')
    
    return df.sort_values('更新日期', ascending=False)

# 3. 定義表格背景顏色邏輯
def highlight_rows(row):
    importance = row['重要性(1-10)']
    if importance >= 9:
        return ['background-color: rgba(255, 75, 75, 0.2)'] * len(row) # 重要性 9-10：淡紅色
    elif importance >= 7:
        return ['background-color: rgba(255, 165, 0, 0.15)'] * len(row) # 重要性 7-8：淡橘色
    return [''] * len(row)

try:
    df = load_data()
    today = datetime.now()

    # --- 側邊欄：進階控制 ---
    st.sidebar.header("🚒 知識庫篩選")
    
    # 功能：時間區間快選
    st.sidebar.subheader("時間範圍")
    time_range = st.sidebar.radio("查看區間", ["全部", "最近 7 天", "最近 30 天"], horizontal=True)
    
    # 功能：關鍵字搜尋
    search_query = st.sidebar.text_input("🔍 關鍵字搜尋", placeholder="搜尋標題、內容或標籤...")
    
    # 功能：多層分類篩選
    mgt_list = ["全部"] + sorted(list(df['管理類別'].dropna().unique()))
    selected_mgt = st.sidebar.selectbox("管理類別 (大項)", mgt_list)
    
    sub_cats = df['類別'].unique() if selected_mgt == "全部" else df[df['管理類別'] == selected_mgt]['類別'].unique()
    selected_sub = st.sidebar.multiselect("詳細類別篩選", sorted(list(sub_cats)), default=list(sub_cats))

    # --- 資料過濾邏輯 ---
    f_df = df[df['類別'].isin(selected_sub)]
    if time_range == "最近 7 天":
        f_df = f_df[f_df['更新日期'] >= (today - timedelta(days=7))]
    elif time_range == "最近 30 天":
        f_df = f_df[f_df['更新日期'] >= (today - timedelta(days=30))]
        
    if search_query:
        mask = f_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        f_df = f_df[mask]

    # --- 主頁面配置 ---
    st.title("🚒 台東分隊大補帖更新紀錄")
    st.caption(f"數據自動同步中 (最後更新：{today.strftime('%H:%M:%S')})")

    # A. 數據速報 (Metric 與 Delta 增長顯示)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📚 總資料筆數", len(df))
    
    # 計算本月更新成長
    this_month_cnt = len(df[df['更新日期'].dt.month == today.month])
    last_month_cnt = len(df[df['更新日期'].dt.month == (today.month - 1 if today.month > 1 else 12)])
    m2.metric("🎯 本月新增", f"{this_month_cnt} 筆", delta=f"{this_month_cnt - last_month_cnt}")
    
    m3.metric("🚨 重大更新 (9+)", len(df[df['重要性(1-10)'] >= 9]))
    m4.metric("📅 篩選結果", len(f_df))

    # B. 重大公告置頂 (重要性 10 的項目)
    urgent = df[df['重要性(1-10)'] == 10].head(1)
    if not urgent.empty:
        st.warning(f"🚨 **重大更新公告：** {urgent.iloc[0]['更新標題']} ({urgent.iloc[0]['更新日期'].strftime('%Y-%m-%d')})")

    st.divider()

    # C. 視覺化統計 (優化為橫向長條圖與趨勢線)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        cat_counts = f_df['類別'].value_counts().reset_index()
        fig_cat = px.bar(cat_counts, x='count', y='index', orientation='h', title='業務領域分佈',
                         labels={'count':'筆數', 'index':'類別'}, color='count', color_continuous_scale='Reds')
        fig_cat.update_layout(showlegend=False, height=350, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cat, use_container_width=True)
    
    with c2:
        trend_df = f_df.resample('M', on='更新日期').size().reset_index(name='件數')
        fig_trend = px.line(trend_df, x='更新日期', y='件數', title='每月更新頻率趨勢', markers=True)
        fig_trend.update_traces(line_color='#FF4B4B', line_width=3)
        fig_trend.update_layout(height=350)
        st.plotly_chart(fig_trend, use_container_width=True)

    # D. 詳細清單表格與匯出
    st.subheader("📋 紀錄清單")
    
    # 匯出按鈕
    csv = f_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 匯出目前篩選報表 (CSV)", data=csv, file_name=f"大補帖_{today.strftime('%Y%m%d')}.csv", mime='text/csv')

    # 表格顯示處理
    display_cols = ['更新日期', '管理類別', '類別', '更新標題', '連結', '重要性(1-10)', '標籤(Tag)']
    plot_df = f_df[display_cols].copy()
    plot_df['更新日期'] = plot_df['更新日期'].dt.strftime('%Y-%m-%d')

    st.dataframe(
        plot_df.style.apply(highlight_rows, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "連結": st.column_config.LinkColumn("相關連結", display_text="🔗 開啟"),
            "重要性(1-10)": st.column_config.NumberColumn("重要性", format="%d ⭐"),
            "更新標題": st.column_config.TextColumn("標題", width="medium")
        }
    )

    # E. 精進功能：詳細內容深挖區 (避免表格太擠)
    st.markdown("---")
    st.subheader("📝 詳細內容檢視")
    all_titles = ["請選擇要查看的項目..."] + list(f_df['更新標題'].unique())
    selected_title = st.selectbox("選取標題以閱讀詳細說明：", all_titles)
    
    if selected_title != "請選擇要查看的項目...":
        detail = f_df[f_df['更新標題'] == selected_title].iloc[0]
        with st.expander(f"📖 查看：{selected_title}", expanded=True):
            col_a, col_b = st.columns(2)
            col_a.write(f"**類別：** {detail['類別']}")
            col_b.write(f"**標籤：** `{detail['標籤(Tag)']}`")
            st.info(detail['詳細內容'] if str(detail['詳細內容']).strip() != "" else "此項目暫無詳細內容說明。")

except Exception as e:
    st.error(f"⚠️ 系統發生錯誤：{e}")
    st.info("請檢查 Google 試算表欄位名稱是否正確，或權限是否已開啟。")
