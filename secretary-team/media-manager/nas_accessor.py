#!/usr/bin/env python3
"""
NAS文件访问器 - 扫描和管理NAS上的媒体文件
支持本地文件系统和WebDAV两种模式
"""

import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

try:
    from webdav3.client import Client as WebDAVClient
    WEBDAV_AVAILABLE = True
except ImportError:
    WEBDAV_AVAILABLE = False


class NASAccessor:
    def __init__(self, config: Dict):
        self.config = config
        nas_config = config.get("nas", {})

        self.nas_type = nas_config.get("type", "local")  # "local" 或 "webdav"
        self.drive_letter = nas_config.get("drive_letter", "Z")
        self.base_path = nas_config.get("base_path", "/")
        self.scan_extensions = nas_config.get("scan_extensions", [])
        self.exclude_folders = nas_config.get("exclude_folders", [])

        # WebDAV 配置
        self.webdav_url = nas_config.get("webdav_url", "")
        self.webdav_username = nas_config.get("webdav_username", "")
        self.webdav_password = nas_config.get("webdav_password", "")
        self.webdav_client = None

        if self.nas_type == "webdav":
            self._init_webdav()

    def _init_webdav(self):
        """初始化 WebDAV 客户端"""
        if not WEBDAV_AVAILABLE:
            print("[NAS] 错误: webdavclient3 未安装，请运行: pip install webdavclient3")
            return

        if not self.webdav_url:
            print("[NAS] 错误: WebDAV URL 未配置")
            return

        options = {
            'webdav_hostname': self.webdav_url,
            'webdav_login': self.webdav_username,
            'webdav_password': self.webdav_password
        }

        try:
            self.webdav_client = WebDAVClient(options)
            print(f"[NAS] WebDAV 客户端初始化成功: {self.webdav_url}")
        except Exception as e:
            print(f"[NAS] WebDAV 客户端初始化失败: {str(e)}")
            self.webdav_client = None

    def _get_nas_root(self) -> str:
        """获取NAS根路径（Windows风格）"""
        return f"{self.drive_letter}:{self.base_path.replace('/', os.sep)}"

    def _is_valid_file(self, filename: str) -> bool:
        """检查文件是否为有效的媒体文件"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.scan_extensions

    def _should_exclude_folder(self, folder_name: str) -> bool:
        """检查是否应排除该文件夹"""
        return folder_name in self.exclude_folders or folder_name.startswith('.')

    def _join_path(self, *parts) -> str:
        """拼接路径（兼容WebDAV）"""
        if self.nas_type == "webdav":
            return '/'.join(parts).replace('//', '/')
        else:
            return os.path.join(*parts)

    def scan_folder(self, folder_path: str = None, recursive: bool = True) -> List[Dict]:
        """
        扫描文件夹中的媒体文件

        Args:
            folder_path: 要扫描的文件夹路径，默认为NAS根目录
            recursive: 是否递归扫描子文件夹

        Returns:
            文件信息列表
        """
        if folder_path is None:
            folder_path = self._get_nas_root()

        if self.nas_type == "webdav":
            return self._webdav_scan_folder(folder_path, recursive)
        else:
            return self._local_scan_folder(folder_path, recursive)

    def _local_scan_folder(self, folder_path: str, recursive: bool) -> List[Dict]:
        """本地文件系统扫描"""
        files = []

        if not os.path.exists(folder_path):
            print(f"[NAS] 路径不存在: {folder_path}")
            return files

        print(f"[NAS] 开始扫描: {folder_path}")

        try:
            if recursive:
                for root, dirs, filenames in os.walk(folder_path):
                    dirs[:] = [d for d in dirs if not self._should_exclude_folder(d)]

                    for filename in filenames:
                        if self._is_valid_file(filename):
                            file_path = os.path.join(root, filename)
                            files.append(self._get_local_file_info(file_path))
            else:
                for entry in os.scandir(folder_path):
                    if entry.is_file() and self._is_valid_file(entry.name):
                        files.append(self._get_local_file_info(entry.path))

            print(f"[NAS] 扫描完成，发现 {len(files)} 个媒体文件")
        except Exception as e:
            print(f"[NAS] 扫描出错: {str(e)}")

        return files

    def _webdav_scan_folder(self, folder_path: str, recursive: bool) -> List[Dict]:
        """WebDAV 扫描"""
        files = []

        if not self.webdav_client:
            print("[NAS] WebDAV 未连接")
            return files

        # 转换路径为 WebDAV 格式
        if folder_path == self._get_nas_root():
            webdav_path = self.base_path
        else:
            # 保留原逻辑，提取相对路径
            webdav_path = folder_path.replace(self._get_nas_root(), '').lstrip(os.sep)
            webdav_path = '/' + webdav_path.replace(os.sep, '/')

        if not webdav_path or webdav_path == '/':
            webdav_path = '/'

        print(f"[NAS] WebDAV 扫描: {webdav_path}")

        try:
            # 获取文件列表
            items = self.webdav_client.list(webdav_path, 0)

            for item_name in items:
                item_path = self._join_path(webdav_path, item_name)

                # 尝试获取详情（判断是文件还是目录）
                try:
                    info = self.webdav_client.info(item_path)
                    if info.get('isdir'):
                        if recursive and not self._should_exclude_folder(item_name):
                            files.extend(self._webdav_scan_folder(
                                self._join_path(folder_path, item_name).replace(os.sep, '/'),
                                recursive
                            ))
                    elif self._is_valid_file(item_name):
                        files.append({
                            "path": item_path,
                            "name": item_name,
                            "ext": os.path.splitext(item_name)[1].lower(),
                            "size": info.get('size', 0),
                            "modified": info.get('modified', ''),
                            "folder": webdav_path
                        })
                except:
                    # 如果 info 失败，尝试当作文件处理
                    if self._is_valid_file(item_name):
                        files.append({
                            "path": item_path,
                            "name": item_name,
                            "ext": os.path.splitext(item_name)[1].lower(),
                            "size": 0,
                            "modified": "",
                            "folder": webdav_path
                        })

            print(f"[NAS] WebDAV 扫描完成，发现 {len(files)} 个媒体文件")
        except Exception as e:
            print(f"[NAS] WebDAV 扫描出错: {str(e)}")

        return files

    def _get_local_file_info(self, file_path: str) -> Dict:
        """获取本地文件信息"""
        stat = os.stat(file_path)
        return {
            "path": file_path,
            "name": os.path.basename(file_path),
            "ext": os.path.splitext(file_path)[1].lower(),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "folder": os.path.dirname(file_path)
        }

    def get_file_list(self, folder_path: str = None) -> List[str]:
        """获取文件夹中的文件列表"""
        if folder_path is None:
            folder_path = self._get_nas_root()

        if self.nas_type == "webdav":
            if not self.webdav_client:
                return []
            try:
                webdav_path = folder_path.replace(self._get_nas_root(), '').lstrip(os.sep)
                webdav_path = '/' + webdav_path.replace(os.sep, '/')
                if webdav_path == '/':
                    webdav_path = '/'
                items = self.webdav_client.list(webdav_path, 0)
                return [i for i in items if not i.endswith('/')]
            except Exception as e:
                print(f"[NAS] WebDAV 获取文件列表失败: {str(e)}")
                return []
        else:
            if not os.path.exists(folder_path):
                return []

            files = []
            for entry in os.scandir(folder_path):
                if entry.is_file():
                    files.append(entry.name)

            return sorted(files)

    def get_folder_list(self, folder_path: str = None) -> List[str]:
        """获取子文件夹列表"""
        if folder_path is None:
            folder_path = self._get_nas_root()

        if self.nas_type == "webdav":
            if not self.webdav_client:
                return []
            try:
                webdav_path = folder_path.replace(self._get_nas_root(), '').lstrip(os.sep)
                webdav_path = '/' + webdav_path.replace(os.sep, '/')
                if webdav_path == '/':
                    webdav_path = '/'
                items = self.webdav_client.list(webdav_path, 0)
                folders = []
                for item in items:
                    try:
                        info = self.webdav_client.info(self._join_path(webdav_path, item))
                        if info.get('isdir') and not self._should_exclude_folder(item):
                            folders.append(item)
                    except:
                        pass
                return sorted(folders)
            except Exception as e:
                print(f"[NAS] WebDAV 获取文件夹列表失败: {str(e)}")
                return []
        else:
            if not os.path.exists(folder_path):
                return []

            folders = []
            for entry in os.scandir(folder_path):
                if entry.is_dir() and not self._should_exclude_folder(entry.name):
                    folders.append(entry.name)

            return sorted(folders)

    def ensure_folder_exists(self, folder_path: str) -> bool:
        """确保文件夹存在，不存在则创建"""
        if self.nas_type == "webdav":
            return self._webdav_ensure_folder_exists(folder_path)
        else:
            return self._local_ensure_folder_exists(folder_path)

    def _local_ensure_folder_exists(self, folder_path: str) -> bool:
        """本地创建文件夹"""
        try:
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print(f"[NAS] 创建文件夹: {folder_path}")
            return True
        except Exception as e:
            print(f"[NAS] 创建文件夹失败: {str(e)}")
            return False

    def _webdav_ensure_folder_exists(self, folder_path: str) -> bool:
        """WebDAV 创建文件夹"""
        if not self.webdav_client:
            return False

        try:
            # 递归创建文件夹
            parts = folder_path.replace(self._get_nas_root(), '').lstrip(os.sep).split(os.sep)
            current = '/'.join(parts)

            # 检查是否已存在
            if not self.webdav_client.check(current):
                self.webdav_client.mkdir(current)
                print(f"[NAS] WebDAV 创建文件夹: {current}")
            return True
        except Exception as e:
            print(f"[NAS] WebDAV 创建文件夹失败: {str(e)}")
            return False

    def move_file(self, source_path: str, dest_path: str) -> bool:
        """移动文件到目标位置"""
        if self.nas_type == "webdav":
            return self._webdav_move_file(source_path, dest_path)
        else:
            return self._local_move_file(source_path, dest_path)

    def _local_move_file(self, source_path: str, dest_path: str) -> bool:
        """本地移动文件"""
        try:
            dest_dir = os.path.dirname(dest_path)
            self.ensure_folder_exists(dest_dir)

            shutil.move(source_path, dest_path)
            print(f"[NAS] 移动文件: {source_path} -> {dest_path}")
            return True
        except Exception as e:
            print(f"[NAS] 移动文件失败: {str(e)}")
            return False

    def _webdav_move_file(self, source_path: str, dest_path: str) -> bool:
        """WebDAV 移动文件"""
        if not self.webdav_client:
            return False

        try:
            dest_dir = os.path.dirname(dest_path)
            self.ensure_folder_exists(dest_dir)

            self.webdav_client.move(source_path, dest_path)
            print(f"[NAS] WebDAV 移动文件: {source_path} -> {dest_path}")
            return True
        except Exception as e:
            print(f"[NAS] WebDAV 移动文件失败: {str(e)}")
            return False

    def copy_file(self, source_path: str, dest_path: str) -> bool:
        """复制文件到目标位置"""
        if self.nas_type == "webdav":
            return self._webdav_copy_file(source_path, dest_path)
        else:
            return self._local_copy_file(source_path, dest_path)

    def _local_copy_file(self, source_path: str, dest_path: str) -> bool:
        """本地复制文件"""
        try:
            dest_dir = os.path.dirname(dest_path)
            self.ensure_folder_exists(dest_dir)

            shutil.copy2(source_path, dest_path)
            print(f"[NAS] 复制文件: {source_path} -> {dest_path}")
            return True
        except Exception as e:
            print(f"[NAS] 复制文件失败: {str(e)}")
            return False

    def _webdav_copy_file(self, source_path: str, dest_path: str) -> bool:
        """WebDAV 复制文件（有限支持）"""
        print("[NAS] WebDAV 复制文件: WebDAV协议不完全支持复制操作")
        return False

    def rename_file(self, old_path: str, new_name: str) -> Optional[str]:
        """重命名文件"""
        if self.nas_type == "webdav":
            return self._webdav_rename_file(old_path, new_name)
        else:
            return self._local_rename_file(old_path, new_name)

    def _local_rename_file(self, old_path: str, new_name: str) -> Optional[str]:
        """本地重命名文件"""
        try:
            folder = os.path.dirname(old_path)
            new_path = os.path.join(folder, new_name)

            os.rename(old_path, new_path)
            print(f"[NAS] 重命名: {old_path} -> {new_path}")
            return new_path
        except Exception as e:
            print(f"[NAS] 重命名失败: {str(e)}")
            return None

    def _webdav_rename_file(self, old_path: str, new_name: str) -> Optional[str]:
        """WebDAV 重命名"""
        if not self.webdav_client:
            return None

        try:
            folder = os.path.dirname(old_path)
            new_path = self._join_path(folder, new_name)

            self.webdav_client.move(old_path, new_path)
            print(f"[NAS] WebDAV 重命名: {old_path} -> {new_path}")
            return new_path
        except Exception as e:
            print(f"[NAS] WebDAV 重命名失败: {str(e)}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        if self.nas_type == "webdav":
            return self._webdav_delete_file(file_path)
        else:
            return self._local_delete_file(file_path)

    def _local_delete_file(self, file_path: str) -> bool:
        """本地删除文件"""
        try:
            os.remove(file_path)
            print(f"[NAS] 删除文件: {file_path}")
            return True
        except Exception as e:
            print(f"[NAS] 删除文件失败: {str(e)}")
            return False

    def _webdav_delete_file(self, file_path: str) -> bool:
        """WebDAV 删除文件"""
        if not self.webdav_client:
            return False

        try:
            self.webdav_client.clean(file_path)
            print(f"[NAS] WebDAV 删除文件: {file_path}")
            return True
        except Exception as e:
            print(f"[NAS] WebDAV 删除文件失败: {str(e)}")
            return False

    def get_file_path(self, *parts) -> str:
        """拼接NAS路径"""
        if self.nas_type == "webdav":
            return '/'.join(parts).replace('//', '/')
        else:
            return os.path.join(self._get_nas_root(), *parts)

    def path_exists(self, path: str) -> bool:
        """检查路径是否存在"""
        if self.nas_type == "webdav":
            if not self.webdav_client:
                return False
            try:
                return self.webdav_client.check(path)
            except:
                return False
        else:
            return os.path.exists(path)

    def check_connection(self) -> bool:
        """检查NAS连接是否正常"""
        if self.nas_type == "webdav":
            return self._check_webdav_connection()
        else:
            return self._check_local_connection()

    def _check_local_connection(self) -> bool:
        """检查本地连接"""
        root = self._get_nas_root()
        exists = os.path.exists(root)

        if exists:
            print(f"[NAS] 连接正常: {root}")
        else:
            print(f"[NAS] 连接失败: {root}")

        return exists

    def _check_webdav_connection(self) -> bool:
        """检查 WebDAV 连接"""
        if not WEBDAV_AVAILABLE:
            print("[NAS] WebDAV 支持未安装 (webdavclient3)")
            return False

        if not self.webdav_client:
            print(f"[NAS] WebDAV 未配置: {self.webdav_url}")
            return False

        try:
            # 尝试列出根目录
            self.webdav_client.list('/', 0)
            print(f"[NAS] WebDAV 连接正常: {self.webdav_url}")
            return True
        except Exception as e:
            print(f"[NAS] WebDAV 连接失败: {str(e)}")
            return False

    def get_folder_structure(self, folder_path: str = None, max_depth: int = 3, current_depth: int = 0) -> Dict:
        """获取文件夹结构树"""
        if folder_path is None:
            folder_path = self._get_nas_root()

        if self.nas_type == "webdav":
            return self._webdav_get_folder_structure(folder_path, max_depth, current_depth)
        else:
            return self._local_get_folder_structure(folder_path, max_depth, current_depth)

    def _local_get_folder_structure(self, folder_path: str, max_depth: int, current_depth: int) -> Dict:
        """获取本地文件夹结构"""
        if current_depth >= max_depth:
            return {"name": os.path.basename(folder_path), "type": "folder"}

        result = {
            "name": os.path.basename(folder_path) or folder_path,
            "type": "folder",
            "children": []
        }

        try:
            for entry in os.scandir(folder_path):
                if entry.is_dir() and not self._should_exclude_folder(entry.name):
                    result["children"].append(
                        self._local_get_folder_structure(entry.path, max_depth, current_depth + 1)
                    )
                elif entry.is_file() and self._is_valid_file(entry.name):
                    result["children"].append({
                        "name": entry.name,
                        "type": "file",
                        "ext": os.path.splitext(entry.name)[1].lower()
                    })
        except Exception as e:
            print(f"[NAS] 读取文件夹失败: {str(e)}")

        return result

    def _webdav_get_folder_structure(self, folder_path: str, max_depth: int, current_depth: int) -> Dict:
        """获取 WebDAV 文件夹结构"""
        if current_depth >= max_depth:
            return {"name": os.path.basename(folder_path), "type": "folder"}

        # 转换路径
        if folder_path == self._get_nas_root():
            webdav_path = '/'
        else:
            webdav_path = folder_path.replace(self._get_nas_root(), '').lstrip(os.sep)
            webdav_path = '/' + webdav_path.replace(os.sep, '/')

        result = {
            "name": os.path.basename(webdav_path) or webdav_path,
            "type": "folder",
            "children": []
        }

        if not self.webdav_client:
            return result

        try:
            items = self.webdav_client.list(webdav_path, 0)

            for item_name in items:
                item_path = self._join_path(webdav_path, item_name)

                try:
                    info = self.webdav_client.info(item_path)
                    if info.get('isdir'):
                        if not self._should_exclude_folder(item_name):
                            result["children"].append(
                                self._webdav_get_folder_structure(
                                    self._join_path(folder_path, item_name).replace(os.sep, '/'),
                                    max_depth,
                                    current_depth + 1
                                )
                            )
                    elif self._is_valid_file(item_name):
                        result["children"].append({
                            "name": item_name,
                            "type": "file",
                            "ext": os.path.splitext(item_name)[1].lower()
                        })
                except:
                    pass

        except Exception as e:
            print(f"[NAS] WebDAV 读取文件夹失败: {str(e)}")

        return result
