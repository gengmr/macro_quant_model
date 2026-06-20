import pandas as pd
import os
import json

# ================= 配置区 =================
DATA_DIR = 'data/raw/宏观经济指标'
OUTPUT_JSON_PATH = 'data/processed_data/macro_indicators.json'

INDICATORS_MAP = {
    # ------ 货币线 ------
    '存款准备金': {'category': '货币线', 'name': '存款准备金率(RRR)'},
    'CPI同比': {'category': '货币线', 'name': '居民消费价格指数同比(CPI)'},
    'm1': {'category': '货币线', 'name': '狭义货币供应量同比(M1)'},
    'm2': {'category': '货币线', 'name': '广义货币供应量同比(M2)'},
    '社融': {'category': '货币线', 'name': '社会融资规模存量同比(AFRE)'},
    'ppi': {'category': '货币线', 'name': '工业生产者出厂价格指数同比(PPI)'},

    # ------ 业绩线 ------
    'gdp': {'category': '业绩线', 'name': '国内生产总值同比(GDP)'},
    '工业利润同比': {'category': '业绩线', 'name': '规模以上工业利润总额同比(Industrial_Profit)'},
    '工业增加值同比': {'category': '业绩线', 'name': '工业增加值同比(IVA)'},
    '固定资产投资': {'category': '业绩线', 'name': '固定资产投资同比(FAI)'},
    '社会消费品零售总额': {'category': '业绩线', 'name': '社会消费品零售总额同比(Retail_Sales)'},
    'pmi': {'category': '业绩线', 'name': '采购经理指数(PMI)'}
}

result_data = {
    "货币线": {},
    "业绩线": {}
}


# ================= 函数区 =================
def extract_timeseries_from_excel(filepath):
    try:
        df = pd.read_excel(filepath, header=None)
    except Exception as e:
        print(f"无法读取文件 {filepath}: {e}")
        return {}

    data_start_idx = -1

    for i in range(len(df)):
        col1_val = df.iloc[i, 0]
        col2_val = df.iloc[i, 1]

        if pd.isna(col1_val) or pd.isna(col2_val):
            continue

        try:
            pd.to_datetime(col1_val)
            float(col2_val)
            data_start_idx = i
            break
        except (ValueError, TypeError):
            continue

    if data_start_idx == -1:
        return {}

    df_data = df.iloc[data_start_idx:, :2].copy()
    df_data.columns = ['Date', 'Value']

    df_data['Date'] = pd.to_datetime(df_data['Date']).dt.strftime('%Y-%m')
    df_data['Value'] = pd.to_numeric(df_data['Value'], errors='coerce')
    df_data = df_data.dropna(subset=['Value'])

    return dict(zip(df_data['Date'], df_data['Value']))


# ================= 主执行区 =================
m1_data_temp = {}
m2_data_temp = {}

if not os.path.exists(DATA_DIR):
    print(f"找不到文件夹 '{DATA_DIR}'，请检查路径。")
else:
    for filename in os.listdir(DATA_DIR):
        if not (filename.endswith('.xlsx') or filename.endswith('.xls')) or filename.startswith('~$'):
            continue

        filepath = os.path.join(DATA_DIR, filename)

        matched_key = None
        for key in INDICATORS_MAP.keys():
            if key in filename:
                matched_key = key
                break

        if not matched_key:
            continue

        raw_data = extract_timeseries_from_excel(filepath)
        if not raw_data:
            continue

        info = INDICATORS_MAP[matched_key]
        category = info['category']
        indicator_name = info['name']

        processed_data = {}
        for date, val in raw_data.items():
            # ======= 格式修改核心区域 =======
            if matched_key in ['CPI同比', 'gdp']:
                # 原数值减去100，并转为四位小数带%的字符串 (例: 105.5 -> "5.5000%")
                processed_data[date] = f"{(val - 100):.4f}%"

            elif matched_key in ['固定资产投资', '社会消费品零售总额']:
                # 不转小数，直接格式化为四位小数带%的字符串 (例: 5.5 -> "5.5000%")
                processed_data[date] = f"{val:.4f}%"

            else:
                # 其他指标统一保留四位有效小数（数字格式）
                processed_data[date] = round(val, 4)
        # ================================

        result_data[category][indicator_name] = processed_data

        # 暂存 m1 和 m2，因为上面其它指标存的仍是数字，这里可以直接相减
        if matched_key == 'm1':
            m1_data_temp = processed_data
        elif matched_key == 'm2':
            m2_data_temp = processed_data

        print(f"成功处理: {filename} -> {indicator_name}")

    # 计算 M1-M2 剪刀差
    if m1_data_temp and m2_data_temp:
        m1_m2_diff = {}
        common_dates = set(m1_data_temp.keys()).intersection(set(m2_data_temp.keys()))

        for date in sorted(common_dates):
            diff = m1_data_temp[date] - m2_data_temp[date]
            m1_m2_diff[date] = round(diff, 4)

        if m1_m2_diff:
            diff_name = "M1-M2剪刀差(M1_M2_Diff)"
            result_data["货币线"][diff_name] = m1_m2_diff
            print(f"M1-M2 剪刀差计算完成，共 {len(m1_m2_diff)} 个月份的数据。")

    # 写入 JSON
    try:
        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=4)
        print(f"\n所有数据已成功导出为: {OUTPUT_JSON_PATH}")
    except Exception as e:
        print(f"写入 JSON 失败: {e}")