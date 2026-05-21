# === 数据探查与预清洗诊断脚本 ===
import io
import pandas as pd

buffer = io.StringIO()

print("--- 数据集概览 ---")
# dfs 包含所有被解析的 DataFrame
if 'dfs' in locals() and dfs:
    for i, df in enumerate(dfs):
        # 【核心修改】读取环境中的 df_names，打印出该表的真实来源
        source_name = df_names[i] if 'df_names' in locals() else f"未知来源"
        print(f"\n[数据表 dfs[{i}] 概况 | 来源: {source_name}]") 
        
        # === 新增：智能表头缺失检测逻辑 ===
        cols = list(df.columns)
        # 判断规则：如果列名是整数、浮点数，或者字符串形式的数字，或者是 Pandas 自动生成的 Unnamed:
        is_no_header = any(
            isinstance(c, (int, float)) or 
            (isinstance(c, str) and c.replace('.', '', 1).isdigit()) or 
            str(c).startswith("Unnamed:") 
            for c in cols
        )
        
        if is_no_header:
            print(f"⚠️ [结构警告]: 检测到当前表头 {cols[:3]} 包含实际数值或无意义占位符，说明用户上传的文件极可能【没有表头】。")
            print(f"👉 [LLM 修复指令 (最高优先级)]: 你的 Python 脚本在处理此数据表时，必须在第一步执行以下代码以找回丢失的第一行数据并重置列名：")
            print(f"    # 还原丢失的第一行")
            print(f"    df.loc[-1] = df.columns")
            print(f"    df.index = df.index + 1")
            print(f"    df = df.sort_index()")
            print(f"    # 重新分配业务列名，请根据数据预览内容自行推断合适的列名")
            print(f"    df.columns = ['字段1', '字段2', ...] ")
        else:
            # 正常表头输出
            print(f"列名列表: {cols}")
        # ====================================

        # 1. 基本信息 (列名已经在上面输出了，这里只输出行列数)
        print(f"行数: {df.shape[0]}, 列数: {df.shape[1]}")
        
        # 2. 缺失值检查
        missing = df.isnull().sum()
        missing = missing[missing > 0]
        if not missing.empty:
            print(f"发现缺失值列:\n{missing.to_string()}")
        else:
            print("无缺失值。")
            
        # 3. 重复值检查
        dupes = df.duplicated().sum()
        print(f"重复行数: {dupes}")
        
        # 4. 数据类型
        print("数据类型:")
        print(df.dtypes.to_string())
        
        # 5. 数据预览 (前10行)
        print("前10行数据预览:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df.head(10).to_string(index=False))
        print("-" * 30)
else:
    print("未检测到数据表。")

result = "数据探查完成"