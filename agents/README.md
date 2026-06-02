# 路漫漫秘书团队 - 使用说明

## 概述

本项目包含5个Agent：
1. **LV (管家)** - 主协调者，协调所有子Agent
2. **飞书助理** - 同步飞书云文档到本地
3. **新闻助理** - 生成每日AI新闻早报
4. **日报助理** - 查看未回复邮件并生成日报
5. **复盘助理** - 引导式复盘对话

## 配置

### 1. 飞书配置
编辑 `config/feishu_config.json`，填入您的飞书应用信息：
```json
{
    "feishu_app_id": "您的App ID",
    "feishu_app_secret": "您的App Secret"
}
```

### 2. 邮箱配置
编辑 `config/email_config.json`，已配置163邮箱：
- IMAP: imap.163.com
- SMTP: smtp.163.com

## 使用方式

### 通过LV管家（推荐）
```bash
# 交互式对话
python agents/lv-coordinator/server.py --interactive

# 指定任务
python agents/lv-coordinator/server.py --request "生成今日新闻早报"
```

### 单独使用各助理

```bash
# 飞书同步
python agents/feishu-sync/server.py --test

# 新闻早报
python agents/news/ai-news/server.py

# 日报生成
python agents/daily-report/server.py

# 复盘对话
python agents/review-agent/server.py --interactive
```

## 输出目录

- 飞书文档: `agents/feishu-sync/docs/`
- 新闻早报: `agents/news/ai-news/output/YYYY-MM-DD/`
- 日报: `agents/daily-report/output/`
- 复盘: `agents/review-agent/output/`