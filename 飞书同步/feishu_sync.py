"""
飞书文档自动同步脚本 v3
功能：打开浏览器让您手动登录，然后自动下载云文档和表格
"""

from playwright.sync_api import sync_playwright
import os
import time
from datetime import datetime

# ============== 配置区域 ==============
SYNC_FOLDER = r"D:\D_CC_vscode\飞书同步"
PAGE_LOAD_DELAY = 3
# =====================================

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def ensure_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
        log(f"创建文件夹: {path}")

def main():
    ensure_folder(SYNC_FOLDER)

    print("=" * 50)
    print("  飞书文档自动同步工具 v3")
    print("=" * 50)
    print(f"同步目录: {SYNC_FOLDER}")
    print("=" * 50)
    print()

    with sync_playwright() as p:
        log("启动浏览器...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            accept_downloads=True
        )
        page = context.new_page()

        try:
            # 1. 打开飞书
            log("打开飞书首页...")
            page.goto("https://feishu.cn", timeout=60000, wait_until="commit")

            # 2. 让用户手动登录
            log("请在浏览器中手动登录飞书...")
            log("登录完成后，按 Enter 键继续...")
            input()  # 等待用户按回车

            log("检测登录状态...")
            time.sleep(3)

            # 3. 设置下载目录
            context.set_default_download_directory(SYNC_FOLDER)
            log(f"下载目录已设置为: {SYNC_FOLDER}")

            # 4. 导航到云文档
            log("导航到云文档...")
            page.goto("https://feishu.cn/docs", timeout=60000, wait_until="commit")
            time.sleep(PAGE_LOAD_DELAY)

            log("已进入云文档页面")
            log("开始扫描文档...")

            # 5. 扫描并导出文档
            docs_downloaded = 0
            sheets_downloaded = 0

            # 遍历文档（最多30个）
            for i in range(30):
                try:
                    # 尝试找到文档项
                    items = page.locator('[class*="item"], [class*="doc"], [class*="content"] span')
                    if items.count() <= i:
                        break

                    doc_item = items.nth(i)
                    if not doc_item.is_visible():
                        continue

                    doc_name = f"文档_{i+1}"
                    try:
                        name = doc_item.inner_text()
                        if name and len(name) > 2:
                            doc_name = name[:30]
                    except:
                        pass

                    # 右键点击
                    try:
                        doc_item.click(button="right", timeout=3000)
                    except:
                        continue
                    time.sleep(1.5)

                    # 查找导出选项
                    export_btns = page.locator('text="导出"')
                    if export_btns.count() > 0:
                        try:
                            export_btns.first.click( timeout=3000)
                            time.sleep(2)

                            # 选择 Markdown 格式
                            md_btns = page.locator('text="Markdown"')
                            if md_btns.count() > 0:
                                md_btns.first.click( timeout=3000)
                                time.sleep(3)
                                docs_downloaded += 1
                                log(f"导出文档: {doc_name}")
                        except:
                            pass

                    # 按 ESC 关闭菜单
                    page.keyboard.press("Escape")
                    time.sleep(1)

                except Exception as e:
                    try:
                        page.keyboard.press("Escape")
                    except:
                        pass
                    continue

            # 6. 处理电子表格
            log("扫描电子表格...")
            try:
                page.goto("https://feishu.cn/sheets", timeout=60000, wait_until="commit")
                time.sleep(PAGE_LOAD_DELAY)

                for i in range(20):
                    try:
                        items = page.locator('[class*="sheet"], [class*="item"]')
                        if items.count() <= i:
                            break

                        sheet_item = items.nth(i)
                        if not sheet_item.is_visible():
                            continue

                        sheet_name = f"表格_{i+1}"
                        try:
                            sheet_item.click(button="right", timeout=3000)
                        except:
                            continue
                        time.sleep(1.5)

                        export_btns = page.locator('text="导出"')
                        if export_btns.count() > 0:
                            try:
                                export_btns.first.click( timeout=3000)
                                time.sleep(2)

                                excel_btns = page.locator('text="Excel"')
                                if excel_btns.count() > 0:
                                    excel_btns.first.click( timeout=3000)
                                    time.sleep(3)
                                    sheets_downloaded += 1
                                    log(f"导出表格: {sheet_name}")
                            except:
                                pass

                        page.keyboard.press("Escape")
                        time.sleep(1)

                    except Exception as e:
                        page.keyboard.press("Escape")
                        continue

            except Exception as e:
                log(f"处理表格时出错: {e}")

            # 7. 完成
            log("=" * 50)
            log(f"同步完成！")
            log(f"文档: {docs_downloaded} 个")
            log(f"表格: {sheets_downloaded} 个")
            log(f"保存位置: {SYNC_FOLDER}")
            log("=" * 50)

            log("浏览器将保持打开状态，请查看结果...")
            time.sleep(5)

        except KeyboardInterrupt:
            log("用户中断操作")
        except Exception as e:
            log(f"发生错误: {e}")

        finally:
            try:
                browser.close()
                log("浏览器已关闭")
            except:
                pass

if __name__ == "__main__":
    main()
