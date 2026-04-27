# -*- coding: utf-8 -*-
"""
BI 数据分析脚本
功能：分析抖音和小红书内容表现，生成诊断报告
使用方法：python bi_analysis.py
"""

import pandas as pd
import sys
import re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')


def load_dy_data():
    """加载抖音数据"""
    dy = pd.read_excel('抖音数据/抖音数据汇总.xlsx', header=None)
    dy.columns = ['标题', '发布时间', '时长类型', '状态', '播放量', '封面点击率', '互动率', '其他1', '完播率', '平均观看时长', '点赞', '评论', '收藏', '转发', '涨粉', '其他2']
    dy['互动数'] = dy['点赞'] + dy['评论'] + dy['收藏'] + dy['转发']
    dy['互动率'] = (dy['互动数'] / dy['播放量'] * 100).round(2)
    dy['发布时间'] = pd.to_datetime(dy['发布时间'])
    return dy


def load_xhs_data():
    """加载小红书数据（自动找最新日期的汇总文件）"""
    import glob
    files = glob.glob('小红书数据/小红书汇总_*.xlsx')
    if not files:
        files = glob.glob('小红书数据/小红书去重汇总.xlsx')
    latest = max(files)
    xhs = pd.read_excel(latest, header=0)
    xhs['互动数'] = xhs['点赞'] + xhs['评论'] + xhs['收藏'] + xhs['分享']
    xhs['互动率'] = (xhs['互动数'] / xhs['观看量'] * 100).round(2)
    xhs['收藏率'] = (xhs['收藏'] / xhs['观看量'] * 100).round(2)
    xhs['曝光点击率'] = (xhs['观看量'] / xhs['曝光'] * 100).round(2)
    xhs['首次发布时间'] = pd.to_datetime(xhs['首次发布时间'])
    return xhs


def get_dy_advice(row, dy_avg_play, dy_avg_gl, dy_avg_wcr):
    """抖音单条诊断"""
    title = str(row['标题'])
    play = row['播放量']
    gl = row['互动率']
    wcr = float(row['完播率']) if row['完播率'] != '-' else 0

    issues = []
    actions = []

    if play >= 2000:
        if gl < 1:
            issues.append('互动率偏低')
            actions.append('增加片尾互动引导')
        actions.append('数据优秀，维持现状')
    elif play >= 1000:
        if gl < 1:
            issues.append('互动率偏低')
            actions.append('增加片尾互动引导')
    elif play >= 500:
        issues.append('播放量中等，有提升空间')
        if gl < 1.5:
            issues.append('互动率可优化')
            actions.append('优化封面/标题提升点击率')
        if wcr < 0.35:
            issues.append('完播率偏低')
            actions.append('开头增加悬念，减少铺垫')
    else:
        issues.append('播放量低')
        if gl > 2:
            actions.append('内容OK，换封面/标题重新发')
        elif gl > 1:
            actions.append('优化标题+封面，提升曝光')
        else:
            issues.append('内容吸引力不足')
            actions.append('重新剪辑或换角度')
        if wcr > 0.45:
            actions.append('完播好，问题在标题/封面')

    zf_rate = row['涨粉'] / play * 100 if play > 0 else 0
    if zf_rate > 1:
        actions.append('涨粉效率高，可继续同类内容')
    if row['转发'] >= 5:
        actions.append('转发高，适合做系列内容')

    issue_str = ' | '.join(set(issues)) if issues else '-'
    action_str = ' -> '.join(set(actions)) if actions else '维持现状'

    return issue_str, action_str


def get_xhs_advice(row):
    """小红书单条诊断"""
    title = str(row['笔记标题'])
    exp = row['曝光']
    view = row['观看量']
    gl = row['互动率']
    sc = row['收藏率']
    click_rate = row['曝光点击率']

    issues = []
    actions = []

    if exp >= 20000:
        if click_rate < 8:
            issues.append('曝光高但封面点击低(%.1f%%)' % click_rate)
            actions.append('换封面重发，或做续集')
        actions.append('数据优秀')
    elif exp >= 10000:
        if click_rate < 8:
            issues.append('封面点击率偏低')
            actions.append('优化封面图')
        if gl > 8:
            actions.append('互动优秀，同角度可继续做')
    elif exp >= 5000:
        if click_rate < 10:
            issues.append('封面/标题点击率有优化空间')
            actions.append('AB测试不同封面')
        if gl > 5:
            actions.append('内容好，可多发同类测试')
    elif exp >= 2000:
        issues.append('曝光量中等')
        if gl > 5:
            actions.append('收藏率高，内容验证OK，换封面多发')
        else:
            issues.append('互动率可提升')
            actions.append('优化封面+发布时间')
    else:
        issues.append('曝光量低')
        if gl > 5 or sc > 3:
            actions.append('内容好，换封面/标题重测')
        elif gl < 2:
            issues.append('内容话题性不足')
            actions.append('换角度重新做')

    if sc > 4:
        actions.append('收藏率超高(%.1f%%)，同系列必做' % sc)
    elif sc > 2 and exp < 5000:
        actions.append('收藏率好(%.1f%%)，封面优化后有爆款潜质' % sc)

    if click_rate > 20:
        actions.append('封面吸引力强，可复用这个封面风格')
    elif click_rate > 30:
        actions.append('封面极优(%.0f%%)，同风格多做' % click_rate)

    issue_str = ' | '.join(set(issues)) if issues else '-'
    action_str = ' -> '.join(set(actions)) if actions else '维持现状'

    return issue_str, action_str


def print_dy_report(dy, dy_avg_play, dy_avg_gl, dy_avg_wcr):
    """打印抖音报告"""
    print('='*100)
    print('【抖音】逐条诊断')
    print('='*100)
    print(f'{"标题":<55} | {"播放":>6} | {"完播":>5} | {"互动":>6} | {"涨粉":>4} | {"发布时间":<12} | 问题 | Action')
    print('-'*150)

    for _, row in dy.sort_values('播放量', ascending=False).iterrows():
        title = str(row['标题'])[:53]
        play = row['播放量']
        wcr = float(row['完播率']) if row['完播率'] != '-' else 0
        gl = row['互动率']
        zf = row['涨粉']
        pub_time = row['发布时间'].strftime('%m-%d %H:%M')

        issue_str, action_str = get_dy_advice(row, dy_avg_play, dy_avg_gl, dy_avg_wcr)

        print(f'{title:<55} | {play:>6.0f} | {wcr:>4.0f}% | {gl:>5.2f}% | {zf:>4.0f} | {pub_time:<12} | {issue_str[:30]} | {action_str[:40]}')


def print_xhs_report(xhs, xhs_avg_exp, xhs_avg_view, xhs_avg_gl, xhs_avg_sc, xhs_avg_click):
    """打印小红书报告"""
    print()
    print('='*120)
    print('【小红书】逐条诊断')
    print('='*120)
    print(f'{"标题":<50} | {"曝光":>7} | {"观看":>5} | {"点击":>5} | {"互动":>5} | {"收藏":>5} | {"涨粉":>4} | {"发布时间":<12} | 问题 | Action')
    print('-'*180)

    for _, row in xhs.sort_values('曝光', ascending=False).iterrows():
        title = str(row['笔记标题'])[:48]
        exp = row['曝光']
        view = row['观看量']
        click_rate = row['曝光点击率']
        gl = row['互动率']
        sc = row['收藏率']
        zf = row['涨粉']
        pub_time = row['首次发布时间'].strftime('%m-%d %H:%M')

        issue_str, action_str = get_xhs_advice(row)

        print(f'{title:<50} | {exp:>7.0f} | {view:>5.0f} | {click_rate:>4.1f}% | {gl:>4.1f}% | {sc:>4.1f}% | {zf:>4.0f} | {pub_time:<12} | {issue_str[:25]} | {action_str[:35]}')


def print_platform_avg(dy, xhs):
    """打印平台平均水平"""
    dy_avg_play = dy['播放量'].mean()
    dy_avg_gl = dy['互动率'].mean()
    dy_wcr = dy[dy['完播率'] != '-']['完播率'].astype(float)
    dy_avg_wcr = dy_wcr.mean()
    dy_avg_zf = dy['涨粉'].mean()

    xhs_avg_exp = xhs['曝光'].mean()
    xhs_avg_view = xhs['观看量'].mean()
    xhs_avg_gl = xhs['互动率'].mean()
    xhs_avg_sc = xhs['收藏率'].mean()
    xhs_avg_click = xhs['曝光点击率'].mean()

    print()
    print('='*80)
    print('【平台平均水平】')
    print('='*80)
    print(f'抖音: 平均播放={dy_avg_play:.0f} | 平均互动率={dy_avg_gl:.2f}% | 平均完播率={dy_avg_wcr*100:.0f}% | 平均涨粉={dy_avg_zf:.0f}')
    print(f'小红书: 平均曝光={xhs_avg_exp:.0f} | 平均观看={xhs_avg_view:.0f} | 平均互动率={xhs_avg_gl:.2f}% | 平均收藏率={xhs_avg_sc:.2f}% | 平均点击率={xhs_avg_click:.2f}%')

    return dy_avg_play, dy_avg_gl, dy_avg_wcr, xhs_avg_exp, xhs_avg_view, xhs_avg_gl, xhs_avg_sc, xhs_avg_click


def print_publish_time_stats(dy, xhs):
    """打印发布时间统计"""
    dy['小时'] = dy['发布时间'].dt.hour
    xhs['小时'] = xhs['首次发布时间'].dt.hour

    print()
    print('='*80)
    print('🕐 最佳发布时间参考（基于现有数据，仅供参考）')
    print('='*80)

    print('\n抖音发布时间效果:')
    dy_hour = dy.groupby('小时').agg({'播放量': ['mean', 'count']}).round(0)
    dy_hour.columns = ['均播放', '条数']
    dy_hour = dy_hour.sort_index()
    for h, row in dy_hour.iterrows():
        print(f'  {h:02d}时: 均播放{row["均播放"]:.0f} ({row["条数"]:.0f}条)')

    print('\n小红书发布时间效果:')
    xhs_hour = xhs.groupby('小时').agg({'曝光': ['mean', 'count']}).round(0)
    xhs_hour.columns = ['均曝光', '条数']
    xhs_hour = xhs_hour.sort_index()
    for h, row in xhs_hour.iterrows():
        print(f'  {h:02d}时: 均曝光{row["均曝光"]:.0f} ({row["条数"]:.0f}条)')


def main():
    print()
    print('='*80)
    print('BI 数据分析报告')
    print(f'更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*80)

    # 加载数据
    dy = load_dy_data()
    xhs = load_xhs_data()

    print(f'\n数据加载完成: 抖音{len(dy)}条 | 小红书{len(xhs)}条')

    # 打印平台平均
    dy_avg_play, dy_avg_gl, dy_avg_wcr, xhs_avg_exp, xhs_avg_view, xhs_avg_gl, xhs_avg_sc, xhs_avg_click = print_platform_avg(dy, xhs)

    # 打印抖音报告
    print_dy_report(dy, dy_avg_play, dy_avg_gl, dy_avg_wcr)

    # 打印小红书报告
    print_xhs_report(xhs, xhs_avg_exp, xhs_avg_view, xhs_avg_gl, xhs_avg_sc, xhs_avg_click)

    # 打印发布时间统计
    print_publish_time_stats(dy, xhs)

    print()
    print('='*80)
    print('分析完成')
    print('='*80)


if __name__ == '__main__':
    main()
