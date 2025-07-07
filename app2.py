import streamlit as st
import pandas as pd
import numpy as np
import random
import statistics
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import plotly.express as px


# 自定义标价，可以录入多个，用逗号隔开
bids = []

st.title("方法二")
st.header("1. 输入所有有效投标报价")
input_bids = st.text_input("用逗号分隔开，可录入多个")

if input_bids:
  bids += input_bids.split(",")
  bids = [float(bid) for bid in bids]
  bids.sort(reverse=True)

if bids:
    # Create a DataFrame for display with a 1-based index
    bids_df = pd.DataFrame({
        '序号': range(1, len(bids) + 1),
        '投标报价': bids
    })
    st.dataframe(bids_df.set_index('序号'))

st.header("2. 调整参数")

# 自定义标价，只能录入一个
K2 = st.number_input('输入自定义数值 K2', value = 0.93, format="%.2f")

# 设置默认的 Q1s 和 K1s
default_Q1s = [0.85, 0.8, 0.75, 0.7, 0.65]
default_K1s = [0.95, 0.96, 0.97, 0.98, 0.99, 1, 1.01]

# 用户自定义 Q1s 和 K1s 输入
input_Q1s = st.text_input("录入Q1，用逗号分隔开：", value=','.join(map(str, default_Q1s)))
input_K1s = st.text_input("录入K1，用逗号分隔开：", value=','.join(map(str, default_K1s)))

# 转换用户输入为浮点数列表，如果转换失败则使用默认值
try:
    Q1s = [float(Q1.strip()) for Q1 in input_Q1s.split(",")]
    K1s = [float(K1.strip()) for K1 in input_K1s.split(",")]
except ValueError:
    st.error("下浮率Δ和下浮系数K必须是由逗号分隔的数字。")
    Q1s = default_Q1s
    K1s = default_K1s

# 第4行: G1 和 G2 (使用内部列布局，让它们在同一行)
st.markdown("---") # 添加分割线
st.write("G1 & G2 设置 (仅当投标数 ≥7 家时生效)")
g_col1, g_col2 = st.columns(2)
with g_col1:
    G1_percent = st.number_input("G1: 去除低价范围 (%)", min_value=0, max_value=49, value=20, step=1)
with g_col2:
    G2_percent = st.number_input("G2: 去除高价范围 (%)", min_value=0, max_value=49, value=20, step=1)

if G1_percent + G2_percent >= 100:
    st.error("G1和G2的百分比之和不能超过100%。")
    st.stop()

# 第5行: B 的来源选择
st.markdown("---") # 添加分割线
b_source = st.radio(
    "选择 B 值来源:",
    ('招标控制价', '自定义最高投标限价'),
    horizontal=True, # 让选项水平排列，更像 "bubble"
    key="b_source"
)
# 根据选择，决定B的值和描述
if b_source == '自定义最高投标限价':
    B = st.number_input('输入最高投标限价', value=1.0, format="%.4f")
    B_description = f"自定义最高投标限价 ({B})"
else:
    B = 1.0  # 招标控制价
    B_description = f"招标控制价 ({B})"

# 设置参数
control_price = 1

# 报价数量
num_bids = len(bids)

# 初始化
df = pd.DataFrame()
A = 0
A_description = "无有效报价"

# 仅当有报价且Q1/K1列表不为空时才继续
if bids and Q1s and K1s:
    bids_for_A_calc = sorted(bids) # 计算A时需要升序列表
    num_bids = len(bids_for_A_calc)

    # 根据报价数量计算 A 值和其描述
    if num_bids >= 7:
        G1 = G1_percent / 100.0
        G2 = G2_percent / 100.0
        remove_low_num = int(round(num_bids * G1))
        remove_high_num = int(round(num_bids * G2))

        if (remove_low_num + remove_high_num) >= num_bids:
            st.error(f"G1({G1_percent}%)和G2({G2_percent}%)设置过高，所有 {num_bids} 个投标均被剔除。请调低G1/G2的值。")
            st.stop()
        
        remaining_bids = bids_for_A_calc[remove_low_num : num_bids - remove_high_num]
        A = statistics.mean(remaining_bids)
        A_description = f"有效投标文件 ≥7 家时，去除最低的 {remove_low_num} 个 ({G1_percent}%) 和最高的 {remove_high_num} 个 ({G2_percent}%) 报价后的算术平均值。"

    elif 4 <= num_bids < 7:
        remaining_bids = bids_for_A_calc[:-1] # 剔除最高报价
        A = statistics.mean(remaining_bids)
        A_description = "有效投标文件 4-6 家时，剔除最高投标报价后的算术平均值。"

    elif 1 <= num_bids < 4:
        if num_bids > 1:
            A = bids_for_A_calc[1] # 次低投标报价
            A_description = "有效投标文件 < 4 家时，取次低投标报价。"
        else: # 只有1个报价
            A = bids_for_A_calc[0]
            A_description = "有效投标文件只有1家，取其投标报价。"
    
    # 生成数据
    data = []
    for Q1 in Q1s:
      for K1 in K1s:
        benchmark = A * K1 * Q1 + B * K2 * (1 - Q1)
        data.append([round(A, 6), Q1, K1, B, K2, round(1 - Q1, 2), round(benchmark, 6)])

    df = pd.DataFrame(data, columns=['A', 'Q1', 'K1', 'B', 'K2', 'Q2 (1-Q1)', '评标基准价'])
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name='序号')


# 确保 df 已定义且不为空再显示结果
if not df.empty:
    st.markdown("### 评标基准价 = A × K1 × Q1 + B × K2 × Q2")
    
    # 参数注解
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
    <small><b>参数注解:</b></small>
    <ul>
      <li><b>A</b> = {A:.6f}。 (计算方式: {A_description})</li>
      <li><b>B</b> = {B:.4f}。 (计算方式: {B_description})</li>
      <li><b>Q2</b> = 1 - Q1。</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # 图表容器
    chart_container = st.container()
    
    bins = st.slider('调整直方图的bin数量:', min_value=1, max_value=len(df['评标基准价']), value=min(30, len(df['评标基准价'])))

    # 计算箱线图的统计数据
    stats = df['评标基准价'].describe(percentiles=[.25, .5, .75])
    min_val, q1_val, median_val, q3_val, max_val = stats['min'], stats['25%'], stats['50%'], stats['75%'], stats['max']
    tickvals = [min_val, q1_val, median_val, q3_val, max_val]
    ticktext = [f"{v:.6f}" for v in tickvals]

    # 创建图表
    fig_box = px.box(df, y='评标基准价', points="all", title="评标基准价分布 - 箱线图")
    fig_box.update_layout(yaxis=dict(tickvals=tickvals, ticktext=ticktext))
    
    fig_hist = px.histogram(df, y='评标基准价', orientation='h', nbins=bins, title="评标基准价分布 - 直方图")
    fig_hist.update_layout(bargap=0.1, yaxis=dict(tickvals=tickvals, ticktext=ticktext), xaxis_title='数量')

    # 并排显示图表
    with chart_container:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.plotly_chart(fig_box, use_container_width=True)
        with chart_col2:
            st.plotly_chart(fig_hist, use_container_width=True)
    
    st.subheader("详细数据表")
    st.dataframe(df)
else:
    st.warning("请输入有效的投标报价并设置参数以生成计算结果。")
