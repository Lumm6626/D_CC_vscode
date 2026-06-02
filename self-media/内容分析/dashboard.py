"""
自媒体内容分析 Dashboard
Flask + ECharts 实现
"""
import os
import pandas as pd
import re
from flask import Flask, render_template, jsonify, request
from datetime import datetime

app = Flask(__name__)

# 数据路径 - 指向正确的数据目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_BASE = r'D:\D_CC_vscode\后台数据'
DY_DIR = os.path.join(DATA_BASE, '抖音数据')
XHS_DIR = os.path.join(DATA_BASE, '小红书数据')


def parse_chinese_date(date_str):
    """解析中文日期格式"""
    if pd.isna(date_str):
        return None
    date_str = str(date_str)
    pattern = r'(\d{4})年(\d{2})月(\d{2})日(\d{2})时(\d{2})分(\d{2})秒'
    match = re.match(pattern, date_str)
    if match:
        year, month, day, hour, minute, second = match.groups()
        return f"{year}-{month}-{day} {hour}:{minute}:{second}"
    return date_str


def load_douyin_data():
    """加载抖音数据"""
    summary_file = os.path.join(DY_DIR, '抖音数据汇总.xlsx')
    if not os.path.exists(summary_file):
        return None

    try:
        df = pd.read_excel(summary_file, header=1)
        # 重命名列
        df.columns = ['标题', '发布时间', '时长', '状态', '播放量', '5s完播率',
                      '平均播放时长', '2s留存率', '点赞数', '评论数', '转发数',
                      '收藏数', '首页浏览量', '粉丝互动率']
        # 转换数值
        for col in ['播放量', '点赞数', '评论数', '转发数', '收藏数']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        # 转换时间
        df['发布时间'] = pd.to_datetime(df['发布时间'], errors='coerce')
        return df
    except Exception as e:
        print(f"加载抖音数据失败: {e}")
        return None


def load_xiaohongshu_data():
    """加载小红书数据"""
    # 尝试去重汇总文件
    summary_file = os.path.join(XHS_DIR, '小红书去重汇总.xlsx')
    if not os.path.exists(summary_file):
        summary_file = os.path.join(XHS_DIR, '小红书数据汇总.xlsx')
    if not os.path.exists(summary_file):
        return None

    try:
        df = pd.read_excel(summary_file, header=1)
        df.columns = ['笔记标题', '首次发布时间', '类型', '曝光数', '浏览数', '互动数',
                      '点赞数', '收藏数', '评论数', '分享数', '是否已发布', '博主回复时间', '笔记']
        # 转换数值
        for col in ['曝光数', '浏览数', '点赞数', '收藏数', '评论数', '分享数']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        # 转换时间
        df['首次发布时间'] = pd.to_datetime(df['首次发布时间'].apply(parse_chinese_date), errors='coerce')
        return df
    except Exception as e:
        print(f"加载小红书数据失败: {e}")
        return None


@app.route('/')
def index():
    """主页面"""
    return render_template('dashboard.html')


@app.route('/api/stats')
def get_stats():
    """获取总体统计"""
    dy_df = load_douyin_data()
    xhs_df = load_xiaohongshu_data()

    stats = {
        'douyin': {},
        'xiaohongshu': {},
        'summary': {}
    }

    if dy_df is not None and len(dy_df) > 0:
        dy_df = dy_df.dropna(subset=['发布时间'])
        stats['douyin'] = {
            'content_count': len(dy_df),
            'total_plays': int(dy_df['播放量'].sum()),
            'total_likes': int(dy_df['点赞数'].sum()),
            'total_comments': int(dy_df['评论数'].sum()),
            'total_shares': int(dy_df['转发数'].sum()),
            'total_favorites': int(dy_df['收藏数'].sum()),
            'avg_play': int(dy_df['播放量'].mean()),
            'avg_like_rate': round(dy_df['点赞数'].sum() / dy_df['播放量'].sum() * 100, 2) if dy_df['播放量'].sum() > 0 else 0,
        }

    if xhs_df is not None and len(xhs_df) > 0:
        xhs_df = xhs_df.dropna(subset=['首次发布时间'])
        stats['xiaohongshu'] = {
            'content_count': len(xhs_df),
            'total_exposures': int(xhs_df['曝光数'].sum()),
            'total_views': int(xhs_df['浏览数'].sum()),
            'total_likes': int(xhs_df['点赞数'].sum()),
            'total_comments': int(xhs_df['评论数'].sum()),
            'total_favorites': int(xhs_df['收藏数'].sum()),
            'total_shares': int(xhs_df['分享数'].sum()),
            'avg_view_rate': round(xhs_df['浏览数'].sum() / xhs_df['曝光数'].sum() * 100, 2) if xhs_df['曝光数'].sum() > 0 else 0,
        }

    # 总体统计
    dy_count = stats['douyin'].get('content_count', 0)
    xhs_count = stats['xiaohongshu'].get('content_count', 0)
    stats['summary'] = {
        'total_content': dy_count + xhs_count,
        'platforms': ['抖音', '小红书'],
        'dy_ratio': round(dy_count / (dy_count + xhs_count) * 100, 1) if (dy_count + xhs_count) > 0 else 0,
        'xhs_ratio': round(xhs_count / (dy_count + xhs_count) * 100, 1) if (dy_count + xhs_count) > 0 else 0,
    }

    return jsonify(stats)


@app.route('/api/trend')
def get_trend():
    """获取发布趋势数据"""
    dy_df = load_douyin_data()
    xhs_df = load_xiaohongshu_data()

    trend = {'dates': [], 'dy_count': [], 'xhs_count': []}

    if dy_df is not None and len(dy_df) > 0:
        dy_df = dy_df.dropna(subset=['发布时间'])
        dy_df['date'] = dy_df['发布时间'].dt.strftime('%Y-%m-%d')
        dy_trend = dy_df.groupby('date').size()

    if xhs_df is not None and xhs_df > 0:
        xhs_df = xhs_df.dropna(subset=['首次发布时间'])
        xhs_df['date'] = xhs_df['首次发布时间'].dt.strftime('%Y-%m-%d')
        xhs_trend = xhs_df.groupby('date').size()

    # 合并日期
    all_dates = set()
    if dy_df is not None: all_dates.update(dy_trend.index)
    if xhs_df is not None: all_dates.update(xhs_trend.index)

    for date in sorted(all_dates):
        trend['dates'].append(date)
        trend['dy_count'].append(int(dy_trend.get(date, 0)))
        trend['xhs_count'].append(int(xhs_trend.get(date, 0)))

    return jsonify(trend)


@app.route('/api/top')
def get_top_content():
    """获取TOP内容"""
    dy_df = load_douyin_data()
    xhs_df = load_xiaohongshu_data()

    top = {'douyin': [], 'xiaohongshu': []}

    if dy_df is not None and len(dy_df) > 0:
        dy_df = dy_df.dropna(subset=['播放量'])
        top_dy = dy_df.nlargest(5, '播放量')[['标题', '播放量', '点赞数', '评论数', '发布时间']]
        top_dy['发布时间'] = top_dy['发布时间'].dt.strftime('%Y-%m-%d')
        top['douyin'] = top_dy.to_dict('records')

    if xhs_df is not None and len(xhs_df) > 0:
        xhs_df = xhs_df.dropna(subset=['浏览数'])
        top_xhs = xhs_df.nlargest(5, '浏览数')[['笔记标题', '浏览数', '点赞数', '收藏数', '首次发布时间']]
        top_xhs['首次发布时间'] = top_xhs['首次发布时间'].dt.strftime('%Y-%m-%d')
        top['xiaohongshu'] = top_xhs.to_dict('records')

    return jsonify(top)


@app.route('/api/engagement')
def get_engagement():
    """获取互动分析"""
    dy_df = load_douyin_data()
    xhs_df = load_xiaohongshu_data()

    engagement = {'douyin': [], 'xiaohongshu': []}

    if dy_df is not None and len(dy_df) > 0:
        dy_df = dy_df.dropna(subset=['播放量'])
        for _, row in dy_df.iterrows():
            total = row['点赞数'] + row['评论数'] + row['收藏数'] + row['转发数']
            engagement['douyin'].append({
                'title': str(row['标题'])[:30] + '...' if len(str(row['标题'])) > 30 else str(row['标题']),
                'likes': int(row['点赞数']),
                'comments': int(row['评论数']),
                'favorites': int(row['收藏数']),
                'shares': int(row['转发数']),
                'total': int(total)
            })

    if xhs_df is not None and len(xhs_df) > 0:
        for _, row in xhs_df.iterrows():
            total = row['点赞数'] + row['评论数'] + row['收藏数'] + row['分享数']
            engagement['xiaohongshu'].append({
                'title': str(row['笔记标题'])[:30] + '...' if len(str(row['笔记标题'])) > 30 else str(row['笔记标题']),
                'likes': int(row['点赞数']),
                'comments': int(row['评论数']),
                'favorites': int(row['收藏数']),
                'shares': int(row['分享数']),
                'total': int(total)
            })

    return jsonify(engagement)


@app.route('/api/refresh')
def refresh_data():
    """刷新数据"""
    try:
        # 运行去重脚本
        dy_script = os.path.join(DY_DIR, '去重合并.py')
        xhs_script = os.path.join(XHS_DIR, '去重合并.py')

        import subprocess
        if os.path.exists(dy_script):
            subprocess.run(['python', dy_script], capture_output=True, timeout=60)
        if os.path.exists(xhs_script):
            subprocess.run(['python', xhs_script], capture_output=True, timeout=60)

        return jsonify({'status': 'success', 'message': '数据已刷新'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == '__main__':
    # 确保模板目录存在
    template_dir = os.path.join(BASE_DIR, 'templates')
    os.makedirs(template_dir, exist_ok=True)

    print(f" Dashboard 启动中...")
    print(f" 抖音数据: {DY_DIR}")
    print(f" 小红书数据: {XHS_DIR}")
    print(f" 访问地址: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
