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
    G1_percent = st.number_input("G1: 去除低价范围 (%)", min_value=0, max_value=49, value=15, step=1)
with g_col2:
    G2_percent = st.number_input("G2: 去除高价范围 (%)", min_value=0, max_value=49, value=15, step=1)

if G1_percent + G2_percent >= 100:
    st.error("G1和G2的百分比之和不能超过100%。")
    st.stop()

# 第5行: B 的来源选择
st.markdown("---") # 添加分割线
b_source = st.radio(
    "选择 B 的值来源:",
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

# 初始化一个空的 DataFrame
df = pd.DataFrame()

# 仅当有报价时才继续
if bids:

  # 排序报价
  bids.sort()

  # 根据报价数量计算去除的报价数
  remove_num = int(round(num_bids * 0.2))

  if num_bids >= 7:
    bids = bids[remove_num:-remove_num]

  elif 4 <= num_bids < 7:
    bids = bids[:-1]

  else:
    bids = bids[1]

  # 计算平均价A
  A = statistics.mean(bids)

  # B为控制价
  B = control_price

  data = []
  for Q1 in Q1s:
    for K1 in K1s:
      benchmark = A * K1 * Q1 + B * K2 * (1-Q1)
      data.append([A, Q1, K1, B, K2, 1-Q1, benchmark])

  df = pd.DataFrame(data, columns=[
    'A', 'Q1', 'K1', 'B', 'K2',
    '1-Q1', 'benchmark'])


# 确保 df 已定义且不为空再显示表格
if not df.empty:
    st.title("评标基准价= A x K1 x Q1 + B x K2 x (1-Q1)")

    # 计算箱线图的统计数据
    stats = df['benchmark'].describe(percentiles=[.25, .5, .75])
    min_val = stats['min']
    q1_val = stats['25%']
    median_val = stats['50%']
    q3_val = stats['75%']
    max_val = stats['max']

    # 设置刻度值和刻度标签，保留小数点六位
    tickvals = [min_val, q1_val, median_val, q3_val, max_val]
    ticktext = [f"{min_val:.6f}", f"{q1_val:.6f}", f"{median_val:.6f}", f"{q3_val:.6f}", f"{max_val:.6f}"]

    # 在图表上方添加滑块以调整直方图的bin数量
    bins = st.slider('调整直方图的bin数量:', min_value=1, max_value=len(df['benchmark']), value=30)

    # 创建箱线图
    fig_box = px.box(df, y='benchmark', points="all")
    fig_box.update_layout(
        autosize=True,
        yaxis=dict(
            tickvals=tickvals,
            ticktext=ticktext
        )
    )
    fig_box.update_yaxes(title='Benchmark')

    # 创建水平直方图并根据滑块的值调整bin的数量
    fig_hist = px.histogram(df, y='benchmark', orientation='h', nbins=bins)
    fig_hist.update_layout(
        bargap=0.1,
        yaxis=dict(
            tickvals=tickvals,
            ticktext=ticktext
        )
    )
    fig_hist.update_xaxes(title='Count')

    # 用 Streamlit 的 columns 创建两列并排显示图表
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(fig_box, use_container_width=True)

    with col2:
        st.plotly_chart(fig_hist, use_container_width=True)

  
    st.subheader("详细数据表")

    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name='序号')
    st.dataframe(df)
else:
    st.error("没有有效的报价数据来计算评标基准价。")
