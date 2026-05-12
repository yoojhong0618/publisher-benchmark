import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 페이지 기본 설정 및 디자인
st.set_page_config(page_title="Global Publisher Benchmark", layout="wide")

# 사이드바 스타일링 (스마일게이트 브랜드 컬러 느낌)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 글로벌 퍼블리셔 세일즈 대시보드")
st.info("경쟁 퍼블리셔의 로우 데이터를 시계열 그래프로 시각화해, 마케팅/세일즈 분석을 지원합니다.")

# 2. 퍼블리셔 선택 (사이드바)
publisher_list = ["Fireshine Games", "Raw Fury (준비 중)"]
selected_pub = st.sidebar.selectbox("📂 분석할 퍼블리셔를 선택하세요", publisher_list)

# 3. 데이터 로드 로직 (엑셀 파일 1개에서 여러 탭 바로 읽기)
@st.cache_data
def load_data(publisher_name):
    # 퍼블리셔별 엑셀 원본 파일명 매핑 (같은 폴더에 엑셀 파일이 있어야 합니다)
    if publisher_name == "Fireshine Games":
        file_path = "VGI - Fireshine Games - Steam historical data.xlsx"
    else:
        file_path = ""
    
    try:
        # sheet_name 파라미터로 엑셀의 특정 탭(Sheet)을 바로 읽어옵니다.
        df_ccu = pd.read_excel(file_path, sheet_name='Daily Avg CCU', parse_dates=['Date'])
        df_rev = pd.read_excel(file_path, sheet_name='Daily Revenue', parse_dates=['Date'])
        df_units = pd.read_excel(file_path, sheet_name='Daily Units Sold', parse_dates=['Date'])
        return df_ccu, df_rev, df_units
        
    except FileNotFoundError:
        st.error(f"'{publisher_name}'의 엑셀 데이터 파일({file_path})을 같은 폴더에서 찾을 수 없습니다.")
        return None, None, None
    except ValueError:
        st.error(f"엑셀 파일 안에 'Daily Avg CCU', 'Daily Revenue' 등의 탭 이름이 정확히 있는지 확인해주세요.")
        return None, None, None

# 데이터 불러오기
df_ccu, df_rev, df_units = load_data(selected_pub)

if df_ccu is not None:
    # 게임 목록 추출 (Date 컬럼 제외)
    game_list = [col for col in df_ccu.columns if col != 'Date']

    # 4. 필터링 영역 (사이드바)
    st.sidebar.divider()
    st.sidebar.subheader("🔍 필터")
    
    # 지표 선택
    metric_map = {
        "동접자 추이 (CCU)": df_ccu,
        "매출 추이 (Revenue)": df_rev,
        "판매량 추이 (Units Sold)": df_units
    }
    selected_metric = st.sidebar.radio("분석 지표", list(metric_map.keys()))
    
    # 게임 다중 선택 (기본값: 상위 3개 게임)
    selected_games = st.sidebar.multiselect(
        "분석 대상 게임",
        options=game_list,
        default=game_list[:3] 
    )

    # 날짜 범위
    min_date, max_date = df_ccu['Date'].min().date(), df_ccu['Date'].max().date()
    date_range = st.sidebar.date_input("조회 기간", value=(min_date, max_date), min_value=min_date, max_value=max_date)

# 5. 메인 대시보드 시각화
    if len(selected_games) > 0 and len(date_range) == 2:
        start_date, end_date = date_range
        target_df = metric_map[selected_metric]
        
        # 1. 날짜 필터링 적용
        mask = (target_df['Date'].dt.date >= start_date) & (target_df['Date'].dt.date <= end_date)
        filtered_df = target_df.loc[mask, ['Date'] + selected_games]

        # 성과순 정렬 로직
        game_sums = filtered_df[selected_games].sum()
        active_games_sums = game_sums[game_sums > 0].sort_values(ascending=False)
        sorted_active_games = active_games_sums.index.tolist()

        if not sorted_active_games:
            st.warning("⚠️ 선택한 기간 동안 성과(데이터)가 있는 게임이 없습니다.")
        else:
            filtered_df = filtered_df[['Date'] + sorted_active_games]

            tab1, tab2 = st.tabs(["📈 지표 변동 추이", "📊 데이터 (Raw)"])

            with tab1:
                custom_colors = px.colors.qualitative.Alphabet + px.colors.qualitative.Light24 + px.colors.qualitative.Dark24
                
                fig = px.line(
                    filtered_df, x='Date', y=sorted_active_games,
                    title=f"[{selected_pub}] {selected_metric} (성과순 정렬)",
                    labels={"value": "수치", "variable": "게임명"},
                    template="plotly_white",
                    color_discrete_sequence=custom_colors
                )
                
                # 상위 8개 게임만 툴팁에 표시하고, 나머지는 숨기기
                top_8_games = sorted_active_games[:8]  # 숫자 8을 원하시는 대로 변경 가능합니다.
                
                fig.for_each_trace(
                    lambda trace: trace.update(hoverinfo='skip') if trace.name not in top_8_games else ()
                )
                
                fig.update_layout(
                    hovermode="x unified",
                    hoverlabel=dict(namelength=-1),
                    legend=dict(traceorder="normal")
                )
                
                # connectgaps를 False로 주어, 데이터가 없는 구간(출시 전)에 억지로 선을 잇거나 0으로 취급하지 않게 확실히 방어합니다.
                fig.update_traces(connectgaps=False)
                
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.dataframe(filtered_df, use_container_width=True)

    else:
        st.warning("👈 좌측 사이드바에서 분석할 게임과 기간을 선택해 주세요.")
