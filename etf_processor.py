import os
import json
import pandas as pd
import numpy as np
from pathlib import Path

# ================= 配置区 =================
RAW_DATA_BASE = Path('data/raw/资产大类/股市/ETF/ETF日线')
SUB_DIRS = ['ETF_Daily_2005_2025', 'ETF_Daily_2026']

PROCESSED_DATA_DIR = Path('data/processed_data')
OUTPUT_DAILY_JSON = PROCESSED_DATA_DIR / 'etf_daily_data.json'
OUTPUT_MONTHLY_JSON = PROCESSED_DATA_DIR / 'etf_monthly_data.json'

FIELDS_ZH = {
    "open": "开盘价", "close": "收盘价", "high": "最高价", "low": "最低价",
    "volume": "成交量", "amount": "成交额", "pct_chg": "涨跌幅", "acc_nav": "累计净值",
    "open_bom": "月初开盘价(Beginning of Month)",
    "close_eom": "月末收盘价(End of Month)",
    "close_avg": "月均收盘价(平滑短期波动)",
    "high_max": "月度最高价", "low_min": "月度最低价",
    "volume_sum": "月度总成交量", "amount_sum": "月度总成交额"
}


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def process_etf_data():
    ensure_dir(PROCESSED_DATA_DIR)
    all_dataframes = []

    print("🚀 开始读取 ETF 原始数据...")
    for sub_dir in SUB_DIRS:
        folder_path = RAW_DATA_BASE / sub_dir
        if not folder_path.exists(): continue

        for file in folder_path.glob('*.csv'):
            try:
                df = pd.read_csv(file)
                if not df.empty and 'datetime' in df.columns and 'code' in df.columns:
                    all_dataframes.append(df)
            except Exception as e:
                print(f"❌ 读取文件 {file.name} 失败: {e}")

    if not all_dataframes:
        print("🛑 未找到有效数据。")
        return

    print("⏳ 正在拼接并清洗日线数据...")
    df_daily = pd.concat(all_dataframes, ignore_index=True)
    df_daily = df_daily.dropna(subset=['code', 'datetime'])
    df_daily['datetime'] = pd.to_datetime(df_daily['datetime'])
    df_daily = df_daily.drop_duplicates(subset=['code', 'datetime'], keep='last')

    df_daily['year_month'] = df_daily['datetime'].dt.strftime('%Y-%m')
    df_daily['datetime_str'] = df_daily['datetime'].dt.strftime('%Y-%m-%d')
    df_daily.sort_values(by=['code', 'datetime'], inplace=True)

    print("📊 正在进行月度数据降频聚合...")
    monthly_agg = df_daily.groupby(['code', 'year_month']).agg(
        open_bom=('open', 'first'),  # 月初开盘价
        close_eom=('close', 'last'),  # 月末收盘价
        close_avg=('close', 'mean'),  # 月均收盘价
        high_max=('high', 'max'),
        low_min=('low', 'min'),
        volume_sum=('volume', 'sum'),
        amount_sum=('amount', 'sum')
    ).reset_index()

    # 精度修约与空值替换
    for col in monthly_agg.columns:
        if monthly_agg[col].dtype == 'float64':
            monthly_agg[col] = monthly_agg[col].round(4)

    df_daily = df_daily.replace({np.nan: None})
    monthly_agg = monthly_agg.replace({np.nan: None})

    print("🏗️ 正在构建分离的 JSON 数据树...")
    json_daily = {"metadata": {"version": "1.0", "type": "daily", "fields": FIELDS_ZH}, "data": {}}
    json_monthly = {"metadata": {"version": "1.0", "type": "monthly", "fields": FIELDS_ZH}, "data": {}}

    grouped_daily = dict(tuple(df_daily.groupby('code')))
    grouped_monthly = dict(tuple(monthly_agg.groupby('code')))

    for code in grouped_daily.keys():
        g_daily = grouped_daily[code]
        fund_name = g_daily['name'].iloc[0] if not g_daily['name'].empty else "未知"

        # 组装日数据
        g_daily_indexed = g_daily.set_index('datetime_str').drop(columns=['code', 'name', 'datetime', 'year_month'],
                                                                 errors='ignore')
        json_daily["data"][code] = {"name": fund_name, "daily_data": g_daily_indexed.to_dict(orient='index')}

        # 组装月数据
        if code in grouped_monthly:
            g_monthly = grouped_monthly[code].set_index('year_month').drop(columns=['code'], errors='ignore')
            json_monthly["data"][code] = {"name": fund_name, "monthly_data": g_monthly.to_dict(orient='index')}

    print(f"💾 正在保存文件...")
    with open(OUTPUT_MONTHLY_JSON, 'w', encoding='utf-8') as f:
        json.dump(json_monthly, f, ensure_ascii=False, indent=2)
    print(f"✅ 月线数据已保存至: {OUTPUT_MONTHLY_JSON}")

    with open(OUTPUT_DAILY_JSON, 'w', encoding='utf-8') as f:
        # 日线数据过大，取消 indent 压缩体积
        json.dump(json_daily, f, ensure_ascii=False)
    print(f"✅ 日线数据已保存至: {OUTPUT_DAILY_JSON}")


if __name__ == "__main__":
    process_etf_data()