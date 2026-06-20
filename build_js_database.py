import json
import os
from pathlib import Path

# ================= 配置区 =================
# 输入文件路径 (前置脚本生成的产物)
MACRO_JSON_PATH = Path('processed_data/macro_indicators.json')
ETF_MONTHLY_JSON_PATH = Path('processed_data/etf_monthly_data.json')

# 输出文件路径 (前端直连的数据底座)
OUTPUT_JS_PATH = Path('../quant_data.js')


def build_js_database():
    print("🚀 开始构建全局 JS 数据底座...")

    # 最终输出的全局数据容器，严格贴合前端所需的命名空间
    merged_data = {
        "宏观经济-货币线": {},
        "宏观经济-业绩线": {},
        "股票数据": {}
    }

    # ================= 1. 加载并挂载宏观经济数据 =================
    if MACRO_JSON_PATH.exists():
        try:
            with open(MACRO_JSON_PATH, 'r', encoding='utf-8') as f:
                macro_raw = json.load(f)

                # 将顶层 Key 映射到标准化命名空间
                if "货币线" in macro_raw:
                    merged_data["宏观经济-货币线"] = macro_raw["货币线"]
                if "业绩线" in macro_raw:
                    merged_data["宏观经济-业绩线"] = macro_raw["业绩线"]
            print(f"✅ 宏观数据合并成功: {MACRO_JSON_PATH.name}")
        except Exception as e:
            print(f"❌ 解析宏观数据失败: {e}")
    else:
        print(f"⚠️ 警告: 未找到宏观数据文件 {MACRO_JSON_PATH}")

    # ================= 2. 加载并重塑 ETF 月频数据 =================
    if ETF_MONTHLY_JSON_PATH.exists():
        try:
            with open(ETF_MONTHLY_JSON_PATH, 'r', encoding='utf-8') as f:
                etf_raw = json.load(f)

                if "data" in etf_raw:
                    for code, info in etf_raw["data"].items():
                        fund_name = info.get("name", "未知资产")
                        monthly_data = info.get("monthly_data", {})

                        # 截取代码的数字部分(例如: 159919.SZ -> 159919)，以匹配前端展示规范
                        clean_code = code.split('.')[0] if '.' in code else code
                        # 拼装为前端字典 Key: "沪深300ETF(159919)"
                        fund_key = f"{fund_name}({clean_code})"

                        merged_data["股票数据"][fund_key] = monthly_data

            print(f"✅ 股票资产合并成功: {ETF_MONTHLY_JSON_PATH.name}")
        except Exception as e:
            print(f"❌ 解析股票数据失败: {e}")
    else:
        print(f"⚠️ 警告: 未找到 ETF 数据文件 {ETF_MONTHLY_JSON_PATH}")

    # ================= 3. 编译并输出为 JS 原生脚本 =================
    print(f"⏳ 正在编译生成 JS 文件...")
    # 确保输出目录存在
    OUTPUT_JS_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(OUTPUT_JS_PATH, 'w', encoding='utf-8') as f:
            # 写入 JS 全局变量声明
            f.write("const QUANT_GLOBAL_DATA = ")
            # 写入合并后的 JSON 实体 (压缩模式，不使用 indent 以减小文件体积)
            json.dump(merged_data, f, ensure_ascii=False)
            # 写入 JS 语句结束符
            f.write(";\n")

        print(f"🎉 编译完成！前端可直接引入使用: {OUTPUT_JS_PATH}")
    except Exception as e:
        print(f"❌ 编译 JS 失败: {e}")


if __name__ == "__main__":
    build_js_database()