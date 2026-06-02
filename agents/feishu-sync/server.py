#!/usr/bin/env python3
"""
飞书助理 (feishu-sync)
功能：读取飞书云文档，同步到本地文件夹
支持自动定时同步
需要 OAuth 授权获取用户 token
"""

import json
import os
import sys
import argparse
import time
import logging
import threading
import webbrowser
from datetime import datetime
from threading import Thread, Event
from urllib.parse import urlencode, parse_qs

try:
    import requests
except ImportError:
    print("错误：需要安装 requests 包，请运行: pip install requests")
    sys.exit(1)

try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CallbackHandler(BaseHTTPRequestHandler):
    """处理 OAuth 回调"""
    code = None

    def do_GET(self):
        global callback_code
        if 'code' in self.path:
            parsed = parse_qs(self.path.split('?')[1])
            code = parsed.get('code', [None])[0]
            if code:
                callback_code = code
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write('<html><body><h1>授权成功！</h1><p>请关闭此窗口，返回命令行。</p></body></html>'.encode())
                # 停止服务器
                threading.Thread(target=self.server.shutdown).start()
                return
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>Waiting for authorization...</h1></body></html>')

    def log_message(self, format, *args):
        pass  # 禁用日志输出


# 全局变量存储回调 code
callback_code = None


class FeishuSync:
    def __init__(self, config_path="config/feishu_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.base_url = "https://open.feishu.cn/open-apis"
        self.user_token = None
        self.token_file = os.path.join(os.path.dirname(__file__), "user_token.json")

    def _load_config(self):
        """加载配置文件"""
        config_file = os.path.join(os.path.dirname(__file__), "..", self.config_path)
        if not os.path.exists(config_file):
            config_file = os.path.join(os.path.dirname(__file__), self.config_path)

        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

    def _save_user_token(self, token_data):
        """保存用户 token"""
        with open(self.token_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, ensure_ascii=False, indent=2)

    def _load_user_token(self):
        """加载用户 token"""
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def start_callback_server(self, port=8080):
        """启动本地回调服务器"""
        server = HTTPServer(('localhost', port), CallbackHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        return server

    def get_user_access_token(self, code=None):
        """获取用户授权的 access_token"""
        # 先尝试加载已保存的 token
        saved_token = self._load_user_token()
        if saved_token:
            expires_at = saved_token.get("expires_at", 0)
            if time.time() < expires_at:
                self.user_token = saved_token.get("access_token")
                print("已加载保存的用户 token")
                return True
            else:
                print("用户 token 已过期，需要重新授权")

        if not code:
            return self._do_oauth()

        return self._exchange_code_for_token(code)

    def _do_oauth(self):
        """引导用户进行 OAuth 授权"""
        global callback_code
        app_id = self.config["feishu_app_id"]
        redirect_uri = self.config.get("oauth_redirect_uri", "http://localhost:8080/callback")

        scopes = ["doc:readonly", "sheet:readonly", "drive:readonly", "wiki:readonly"]

        params = {
            "app_id": app_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "response_type": "code",
            "state": "feishu_sync"
        }

        auth_url = f"{self.base_url}/authen/v1/authorize?" + urlencode(params)

        print("=" * 60)
        print("需要授权才能访问你的飞书文档")
        print("=" * 60)
        print(f"\n1. 启动本地回调服务器...")
        server = self.start_callback_server()
        print(f"   服务器已启动 (localhost:8080)")
        print(f"\n2. 正在打开浏览器授权...")
        webbrowser.open(auth_url)
        print(f"   (如果浏览器没有自动打开，请手动复制以下链接到浏览器)\n")
        print(f"   {auth_url}")
        print(f"\n3. 等待授权回调...")
        print("   (授权成功后，此窗口会显示成功信息)\n")

        # 等待回调（最多等5分钟）
        wait_count = 0
        while callback_code is None and wait_count < 300:
            time.sleep(1)
            wait_count += 1

        if callback_code:
            code = callback_code
            callback_code = None  # 重置
            return self._exchange_code_for_token(code)
        else:
            print("授权超时，请重试")
            return False

    def _exchange_code_for_token(self, code):
        """用授权码换取用户 token"""
        url = f"{self.base_url}/authen/v1/oidc/access_token"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"grant_type": "authorization_code", "code": code}

        app_token = self._get_app_access_token()
        if not app_token:
            return False

        headers["Authorization"] = f"Bearer {app_token}"

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        if result.get("code") == 0:
            token_data = result.get("data", {})
            self.user_token = token_data.get("access_token")

            expires_in = token_data.get("expires_in", 0)
            save_data = {
                "access_token": self.user_token,
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": time.time() + expires_in - 300
            }
            self._save_user_token(save_data)

            print("\n*** 用户授权成功！ ***\n")
            return True
        else:
            print(f"获取用户 token 失败: {result.get('msg', '未知错误')}")
            return False

    def _get_app_access_token(self):
        """获取 app 级别的 access_token"""
        url = f"{self.base_url}/auth/v3/app_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "app_id": self.config["feishu_app_id"],
            "app_secret": self.config["feishu_app_secret"]
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        if result.get("code") == 0:
            return result.get("app_access_token")
        else:
            print(f"获取 app token 失败: {result.get('msg', '未知错误')}")
            return None

    def refresh_user_token(self):
        """刷新用户 token"""
        saved_token = self._load_user_token()
        if not saved_token or not saved_token.get("refresh_token"):
            print("没有 refresh_token，需要重新授权")
            return self._do_oauth()

        url = f"{self.base_url}/authen/v1/oidc/refresh_access_token"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"grant_type": "refresh_token", "refresh_token": saved_token["refresh_token"]}

        app_token = self._get_app_access_token()
        if not app_token:
            return False

        headers["Authorization"] = f"Bearer {app_token}"

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        if result.get("code") == 0:
            token_data = result.get("data", {})
            self.user_token = token_data.get("access_token")

            expires_in = token_data.get("expires_in", 0)
            save_data = {
                "access_token": self.user_token,
                "refresh_token": token_data.get("refresh_token", saved_token.get("refresh_token")),
                "expires_at": time.time() + expires_in - 300
            }
            self._save_user_token(save_data)

            print("用户 token 刷新成功！")
            return True
        else:
            print(f"刷新 token 失败: {result.get('msg', '未知错误')}")
            return False

    def get_user_info(self):
        """获取当前用户信息"""
        if not self.user_token:
            if not self.get_user_access_token():
                return None

        url = f"{self.base_url}/authen/v1/user_info"
        headers = {"Authorization": f"Bearer {self.user_token}"}

        response = requests.get(url, headers=headers)
        result = response.json()

        if result.get("code") == 0:
            return result.get("data", {})
        else:
            print(f"获取用户信息失败: {result.get('msg', '未知错误')}")
            if result.get("code") == 99991668:
                if self.refresh_user_token():
                    return self.get_user_info()
            return None

    def get_docs_list(self, doc_type=None):
        """获取云空间文档列表"""
        if not self.user_token:
            saved = self._load_user_token()
            if saved:
                self.user_token = saved.get("access_token")

        if not self.user_token:
            print("没有有效的 user token，需要先授权")
            return []

        headers = {"Authorization": f"Bearer {self.user_token}"}

        all_docs = []

        user_info = self.get_user_info()
        if not user_info:
            return []

        user_id = user_info.get("user_id")
        print(f"用户ID: {user_id}")

        url = f"{self.base_url}/drive/v1/users/{user_id}/files"
        node_types = [doc_type] if doc_type else ["doc", "sheet", "bitable", "mindnote", "shortcut"]

        for node_type in node_types:
            params = {
                "page_size": 50,
                "order_by": "created_time",
                "direction": "DESC",
                "node_type": node_type
            }

            try:
                response = requests.get(url, headers=headers, params=params)
                result = response.json()

                if result.get("code") == 0:
                    items = result.get("data", {}).get("items", [])
                    for item in items:
                        if item.get("type") == node_type or item.get("node_type") == node_type:
                            all_docs.append(item)
                    print(f"类型 {node_type} 找到 {len(items)} 个文件")
                else:
                    print(f"获取文档列表失败({node_type}): {result.get('msg', '未知错误')}")
            except Exception as e:
                print(f"获取文档异常({node_type}): {str(e)}")

        # 去重
        seen_tokens = set()
        unique_docs = []
        for doc in all_docs:
            token = doc.get("token", "")
            if token and token not in seen_tokens:
                seen_tokens.add(token)
                unique_docs.append(doc)

        return unique_docs

    def get_doc_content(self, token, doc_type="doc"):
        """获取文档内容"""
        if not self.user_token:
            saved = self._load_user_token()
            if saved:
                self.user_token = saved.get("access_token")

        headers = {"Authorization": f"Bearer {self.user_token}"}

        try:
            if doc_type == "doc":
                url = f"{self.base_url}/doc/v1/documents/{token}/content"
                response = requests.get(url, headers=headers)
            elif doc_type == "sheet":
                url = f"{self.base_url}/sheets/v2/spreadsheets/{token}/values"
                response = requests.get(url, headers=headers)
            elif doc_type == "bitable":
                url = f"{self.base_url}/bitable/v1/app/{token}/records"
                response = requests.get(url, headers=headers)
            else:
                url = f"{self.base_url}/doc/v1/documents/{token}/content"
                response = requests.get(url, headers=headers)

            result = response.json()

            if result.get("code") == 0:
                return result.get("data", {})
            else:
                print(f"获取文档内容失败: {result.get('msg', '未知错误')}")
                if result.get("code") == 99991668:
                    if self.refresh_user_token():
                        return self.get_doc_content(token, doc_type)
                return None
        except Exception as e:
            print(f"获取文档内容异常: {str(e)}")
            return None

    def sync_docs(self):
        """同步文档到本地"""
        sync_folder = self.config.get("sync_folder", "docs")
        os.makedirs(sync_folder, exist_ok=True)

        print(f"\n开始同步飞书云文档到: {sync_folder}\n")

        docs = self.get_docs_list()
        print(f"\n共找到 {len(docs)} 个文档\n")

        synced_count = 0

        for doc in docs:
            doc_type = doc.get("type", "")
            doc_name = doc.get("name", "untitled")
            doc_token = doc.get("token", "")

            if not doc_token:
                continue

            if doc_type not in ["doc", "sheet", "bitable"]:
                continue

            safe_name = "".join(c for c in doc_name if c.isalnum() or c in " _-").strip()
            if not safe_name:
                safe_name = f"doc_{doc_token[:8]}"

            ext = ".txt"
            if doc_type in ["sheet", "bitable"]:
                ext = ".csv"
            else:
                ext = ".md"

            filename = f"{safe_name}{ext}"
            filepath = os.path.join(sync_folder, filename)

            content = self.get_doc_content(doc_token, doc_type)

            if content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(content, ensure_ascii=False, indent=2))
                print(f"  已同步: {filename}")
                synced_count += 1
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {doc_name}\n\n(内容获取失败)")
                print(f"  已创建占位符: {filename}")

        print(f"\n同步完成，共同步 {synced_count} 个文档\n")
        return synced_count

    def run(self):
        """运行同步"""
        try:
            self.sync_docs()
        except Exception as e:
            print(f"同步失败: {str(e)}")
            return 1
        return 0

    def run_auto_sync(self, interval_minutes=30):
        """自动定时同步"""
        print(f"启动自动同步服务，间隔 {interval_minutes} 分钟")
        print("按 Ctrl+C 停止服务\n")

        if not self.user_token:
            saved = self._load_user_token()
            if saved:
                self.user_token = saved.get("access_token")
            else:
                print("没有找到已保存的 token，请先进行授权")
                if not self.get_user_access_token():
                    print("授权失败，无法启动自动同步")
                    return

        self._auto_sync_once()

        stop_event = Event()
        last_sync_time = None

        while not stop_event.is_set():
            if last_sync_time is None:
                next_sync = interval_minutes * 60
            else:
                elapsed = time.time() - last_sync_time
                next_sync = interval_minutes * 60 - elapsed
                if next_sync < 0:
                    next_sync = 0

            for _ in range(int(next_sync / 60) + 1):
                if stop_event.is_set():
                    break
                time.sleep(min(60, next_sync if _ == 0 else 60))

            if stop_event.is_set():
                break

            last_sync_time = time.time()
            self._auto_sync_once()

    def _auto_sync_once(self):
        """执行一次自动同步"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'='*50}")
            print(f"自动同步开始: {now}")
            print(f"{'='*50}")
            synced = self.sync_docs()
            logger.info(f"自动同步完成，共同步 {synced} 个文档")
        except Exception as e:
            logger.error(f"自动同步失败: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="飞书云文档同步工具")
    parser.add_argument("--config", default="config/feishu_config.json",
                        help="配置文件路径")
    parser.add_argument("--test", action="store_true",
                        help="测试连接")
    parser.add_argument("--auto", action="store_true",
                        help="启动自动同步模式")
    parser.add_argument("--interval", type=int, default=30,
                        help="自动同步间隔，单位分钟 (默认30分钟)")
    parser.add_argument("--auth", action="store_true",
                        help="进行OAuth授权")

    args = parser.parse_args()

    sync = FeishuSync(args.config)

    if args.auth:
        sync.get_user_access_token()
    elif args.test:
        if sync.get_user_access_token():
            print("飞书API连接成功！")
            docs = sync.get_docs_list()
            print(f"共找到 {len(docs)} 个文档")
        else:
            print("飞书API连接失败，请检查配置或进行授权")
            return 1
    elif args.auto:
        interval = args.interval
        if interval == 30:
            interval = sync.config.get("auto_sync_interval_minutes", 30)
        sync.run_auto_sync(interval_minutes=interval)
    else:
        return sync.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
