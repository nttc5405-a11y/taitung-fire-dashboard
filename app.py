import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. 網頁設定
st.set_page_config(
    page_title="台東分隊大補帖管理系統",
    page_icon="🚒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 資料讀取 (ID 已帶入)
# SHEET_ID = "1gi-0Lgy16kTp_S806AIivIUlC0m-_q9-uZPEZY5mLY4"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTD3BDxVvOoKEEiqIC02C85oRWRIBoxYVRmsZUMaVgsge9pUJwGYBQMi4XXgSSNnOtPaR8ZtKCbrUuG/pub?output=csv"

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        # 必要欄位檢查
        expected_cols = ['更新日期', '管理類別', '類別', '更新標題', '連結', '重要性(1-10)', '標籤(Tag)', '詳細內容']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
                
        df['更新日期'] = pd.to_datetime(df['更新日期'], errors='coerce')
        df = df.dropna(subset=['更新日期'])
        df['重要性(1-10)'] = pd.to_numeric(df['重要性(1-10)'], errors='coerce').fillna(0)
        return df.sort_values('更新日期', ascending=False)
    except Exception as e:
        st.error(f"資料加載失敗：{e}")
        return pd.DataFrame()

def highlight_rows(row):
    importance = row['重要性(1-10)']
    if importance >= 9: return ['background-color: rgba(255, 75, 75, 0.2)'] * len(row)
    if importance >= 7: return ['background-color: rgba(255, 165, 0, 0.15)'] * len(row)
    return [''] * len(row)

try:
    df = load_data()
    if df.empty:
        st.warning("目前無可用資料，請確認試算表連結與權限。")
        st.stop()

    today = datetime.now()

    # --- 側邊欄 ---
    st.sidebar.header("🚒 知識庫篩選")
    time_range = st.sidebar.radio("查看區間", ["全部", "最近 7 天", "最近 30 天"], index=0, horizontal=True)
    search_query = st.sidebar.text_input("🔍 關鍵字搜尋", placeholder="搜尋標題、內容或標籤...")
    
    mgt_list = ["全部"] + sorted([str(x) for x in df['管理類別'].dropna().unique()])
    selected_mgt = st.sidebar.selectbox("管理類別 (大項)", mgt_list)
    
    sub_cats = df['類別'].unique() if selected_mgt == "全部" else df[df['管理類別'] == selected_mgt]['類別'].unique()
    selected_sub = st.sidebar.multiselect("詳細類別篩選", sorted([str(x) for x in sub_cats]), default=[str(x) for x in sub_cats])

    # --- 過濾邏輯 ---
    f_df = df[df['類別'].isin(selected_sub)]
    if time_range == "最近 7 天":
        f_df = f_df[f_df['更新日期'] >= (today - timedelta(days=7))]
    elif time_range == "最近 30 天":
        f_df = f_df[f_df['更新日期'] >= (today - timedelta(days=30))]
        
    if search_query:
        mask = f_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        f_df = f_df[mask]

    # --- 主頁面 ---
    st.title("🚒 台東分隊大補帖更新紀錄")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📚 總資料筆數", len(df))
    
    this_month_cnt = len(df[df['更新日期'].dt.month == today.month])
    last_month_cnt = len(df[df['更新日期'].dt.month == (today.month - 1 if today.month > 1 else 12)])
    m2.metric("🎯 本月新增", f"{this_month_cnt} 筆", delta=f"{this_month_cnt - last_month_cnt}")
    m3.metric("🚨 重大更新 (9+)", len(df[df['重要性(1-10)'] >= 9]))
    m4.metric("📅 篩選結果", len(f_df))

    st.divider()

    if len(f_df) > 0:
        # B. 視覺化圖表
        c1, c2 = st.columns([1, 1.2])
        with c1:
            # 修正關鍵點：將 y='index' 改為 y='類別'
            cat_counts = f_df['類別'].value_counts().reset_index()
            # 在新版 Pandas 中，reset_index() 會產生 ['類別', 'count'] 欄位
            fig_cat = px.bar(cat_counts, x='count', y='類別', orientation='h', title='業務領域分佈',
                             labels={'count':'筆數', '類別':'類別'}, color='count', color_continuous_scale='Reds')
            fig_cat.update_layout(showlegend=False, height=350, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_cat, use_container_width=True)
        
        with c2:
            trend_df = f_df.resample('M', on='更新日期').size().reset_index(name='件數')
            if not trend_df.empty:
                fig_trend = px.line(trend_df, x='更新日期', y='件數', title='每月更新頻率趨勢', markers=True)
                fig_trend.update_traces(line_color='#FF4B4B', line_width=3)
                fig_trend.update_layout(height=350)
                st.plotly_chart(fig_trend, use_container_width=True)

        # C. 紀錄表格
        st.subheader("📋 紀錄清單")
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
        
        # D. 詳細內容
        st.markdown("---")
        st.subheader("📝 詳細內容檢視")
        all_titles = ["請選擇..."] + list(f_df['更新標題'].unique())
        selected_title = st.selectbox("選取標題閱讀詳細說明：", all_titles)
        if selected_title != "請選擇...":
            detail = f_df[f_df['更新標題'] == selected_title].iloc[0]
            with st.expander(f"📖 查看：{selected_title}", expanded=True):
                st.info(detail['詳細內容'] if str(detail['詳細內容']).strip() != "" else "此項目暫無詳細說明。")
                
    else:
        st.warning("⚠️ 目前篩選條件下沒有資料，請嘗試調整側邊欄的篩選條件。")

except Exception as e:
    st.error(f"⚠️ 系統異常：{e}")
