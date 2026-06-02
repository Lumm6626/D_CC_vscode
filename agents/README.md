# 路漫漫秘书团队 - 使用说明

## 概述

本项目包含以下Agent：
1. **LV (管家)** - 主协调者，协调所有子Agent
2. **新闻助理** - 生成每日AI新闻早报
3. **医疗器械新闻助理** - 生成医疗器械行业新闻
4. **过敏新闻日报** - 过敏诊所行业新闻日报
5. **媒体管家** - NAS媒体文件扫描、分类、重命名
6. **设计师 (Designer)** - 前端界面设计、图片设计、UI/UX，输出设计规范和React代码
7. **工程师 (Engineer)** - 后端功能和代码开发（FastAPI），按API契约交付
8. **代码审查 (Code Review)** - 审查代码质量、安全漏洞、逻辑正确性
9. **自我进化助理** - 记录和分析工作历史

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
# AI新闻早报
python agents/news/ai-news/server.py

# 医疗器械新闻
python agents/news/medical-device-news/server.py

# 媒体管理
python agents/media-manager/server.py

# 设计师
python agents/designer/server.py

# 工程师
python agents/engineer/server.py

# 复盘对话
python agents/review-agent/server.py --interactive
```

## 配置

编辑 `agents/config/` 下的对应配置文件。

## 输出目录

- 新闻早报: `agents/news/ai-news/output/YYYY-MM-DD/`
- 医疗器械新闻: `agents/news/medical-device-news/output/YYYY-MM-DD/`
- 过敏新闻: `agents/news/allergy-news-daily/output/`
- 媒体管理: `agents/media-manager/output/`
- 复盘: `agents/review-agent/output/`
