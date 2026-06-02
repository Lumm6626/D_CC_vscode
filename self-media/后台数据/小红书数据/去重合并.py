"""
小红书数据去重合并脚本
使用方法：将所有小红书数据Excel文件放入本目录，直接运行脚本
去重规则：按"笔记标题"去重，保留"首次发布时间"最新的一条
"""
import pandas as pd
import re
import os
from datetime import datetime

def parse_chinese_date(date_str):
    """解析中文日期格式 2026年04月06日12时37分01秒"""
    if pd.isna(date_str):
        return pd.NaT
    date_str = str(date_str)
    pattern = r'(\d{4})年(\d{2})月(\d{2})日(\d{2})时(\d{2})分(\d{2})秒'
    match = re.match(pattern, date_str)
    if match:
        year, month, day, hour, minute, second = match.groups()
        return f"{year}-{month}-{day} {hour}:{minute}:{second}"
    return date_str

def get_all_excel_files(folder_path):
    """获取文件夹下所有Excel文件，排除汇总文件和临时文件"""
    files = []
    for f in os.listdir(folder_path):
        if f.endswith('.xlsx') and not f.startswith('~$') and '汇总' not in f and '去重' not in f:
            files.append(f)
    return sorted(files)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_files = get_all_excel_files(script_dir)

    if not excel_files:
        print("未找到Excel文件（排除汇总文件）")
        return

    print(f"找到 {len(excel_files)} 个数据文件:")
    for f in excel_files:
        print(f"  - {f}")

    all_data = []
    for f in excel_files:
        filepath = os.path.join(script_dir, f)
        try:
            # 小红书数据通常是header=1
            df = pd.read_excel(filepath, header=1)
            all_data.append(df)
            print(f"成功读取: {f} ({len(df)} 条)")
        except Exception as e:
            print(f"读取失败 {f}: {e}")

    if not all_data:
        print("没有成功读取任何数据")
        return

    # 合并所有数据
    df_merged = pd.concat(all_data, ignore_index=True)
    print(f"\n合并后总数: {len(df_merged)}")

    # 查找标题列和时间列
    title_col = None
    time_col = None
    for col in df_merged.columns:
        if '标题' in col and title_col is None:
            title_col = col
        if '时间' in col or '发布' in col:
            time_col = col

    print(f"标题列: {title_col}, 时间列: {time_col}")

    if title_col and time_col:
        # 转换时间
        df_merged[time_col] = df_merged[time_col].apply(parse_chinese_date)
        df_merged[time_col] = pd.to_datetime(df_merged[time_col])
        # 去重
        df_merged = df_merged.sort_values(time_col, ascending=False).drop_duplicates(subset=[title_col], keep='first')
        print(f"去重后总数: {len(df_merged)}")

    # 保存
    output_file = os.path.join(script_dir, f'小红书汇总_{datetime.now().strftime("%Y%m%d")}.xlsx')
    df_merged.to_excel(output_file, index=False)
    print(f"\n已保存到: {output_file}")

if __name__ == "__main__":
    main()
