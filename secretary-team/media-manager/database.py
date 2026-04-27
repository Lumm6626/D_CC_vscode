#!/usr/bin/env python3
"""
媒体素材数据库管理
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict


class MediaDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__),
                "output", "media_library.db"
            )
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 媒体文件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                ai_generated_name TEXT,
                scene_category TEXT,
                tags TEXT,
                description TEXT,
                rename_status TEXT DEFAULT 'pending',
                new_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_batch TEXT
            )
        """)

        # 场景分类表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scene_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                keywords TEXT NOT NULL,
                target_folder TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 命名历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS naming_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                new_name TEXT NOT NULL,
                naming_method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (media_id) REFERENCES media_files(id)
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_scene ON media_files(scene_category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_type ON media_files(file_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_path ON media_files(original_path)")

        conn.commit()
        conn.close()

    def add_media_file(self, file_path: str, filename: str, file_type: str,
                       file_size: int = 0, scan_batch: str = None) -> int:
        """添加媒体文件记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if scan_batch is None:
            scan_batch = datetime.now().strftime("%Y%m%d%H%M%S")

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO media_files
                (original_path, filename, file_type, file_size, scan_batch, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (file_path, filename, file_type, file_size, scan_batch))

            media_id = cursor.lastrowid if cursor.lastrowid else cursor.execute(
                "SELECT id FROM media_files WHERE original_path = ?", (file_path,)
            ).fetchone()[0]

            conn.commit()
            return media_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_media_info(self, media_id: int, **kwargs):
        """更新媒体文件信息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        allowed_fields = ['ai_generated_name', 'scene_category', 'tags',
                         'description', 'rename_status', 'new_path']

        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(media_id)

            cursor.execute(f"""
                UPDATE media_files SET {', '.join(updates)} WHERE id = ?
            """, values)
            conn.commit()

        conn.close()

    def get_media_by_id(self, media_id: int) -> Optional[Dict]:
        """根据ID获取媒体文件"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM media_files WHERE id = ?", (media_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_media_by_path(self, path: str) -> Optional[Dict]:
        """根据路径获取媒体文件"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM media_files WHERE original_path = ?", (path,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def search_media(self, keyword: str = None, scene: str = None,
                     file_type: str = None, limit: int = 100) -> List[Dict]:
        """搜索媒体文件"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM media_files WHERE 1=1"
        params = []

        if keyword:
            query += " AND (filename LIKE ? OR ai_generated_name LIKE ? OR description LIKE ? OR tags LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw, kw])

        if scene:
            query += " AND scene_category = ?"
            params.append(scene)

        if file_type:
            query += " AND file_type = ?"
            params.append(file_type)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_all_scenes(self) -> List[str]:
        """获取所有场景分类"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT scene_category FROM media_files WHERE scene_category IS NOT NULL")
        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    def get_scene_stats(self) -> List[Dict]:
        """获取各场景统计"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT scene_category,
                   COUNT(*) as count,
                   SUM(CASE WHEN rename_status = 'completed' THEN 1 ELSE 0 END) as renamed
            FROM media_files
            GROUP BY scene_category
            ORDER BY count DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def add_naming_history(self, media_id: int, original_name: str,
                          new_name: str, naming_method: str = "rule"):
        """添加命名历史"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO naming_history (media_id, original_name, new_name, naming_method)
            VALUES (?, ?, ?, ?)
        """, (media_id, original_name, new_name, naming_method))

        conn.commit()
        conn.close()

    def get_naming_history(self, media_id: int) -> List[Dict]:
        """获取文件命名历史"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM naming_history WHERE media_id = ? ORDER BY created_at DESC
        """, (media_id,))
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_pending_files(self, scene: str = None, limit: int = 50) -> List[Dict]:
        """获取待处理的文件"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM media_files WHERE rename_status = 'pending'"
        params = []

        if scene:
            query += " AND scene_category = ?"
            params.append(scene)

        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def mark_as_renamed(self, media_id: int, new_name: str, new_path: str):
        """标记文件已重命名"""
        self.update_media_info(
            media_id,
            ai_generated_name=new_name,
            new_path=new_path,
            rename_status='completed'
        )

    def save_scene_config(self, scenes: List[Dict]):
        """保存场景配置"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM scene_categories")

        for scene in scenes:
            cursor.execute("""
                INSERT INTO scene_categories (name, keywords, target_folder)
                VALUES (?, ?, ?)
            """, (scene['name'], json.dumps(scene['keywords'], ensure_ascii=False), scene['target_folder']))

        conn.commit()
        conn.close()

    def get_scene_config(self) -> List[Dict]:
        """获取场景配置"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM scene_categories")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_total_stats(self) -> Dict:
        """获取总体统计"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN rename_status = 'completed' THEN 1 ELSE 0 END) as renamed,
                SUM(CASE WHEN scene_category IS NULL THEN 1 ELSE 0 END) as unclassified,
                SUM(file_size) as total_size
            FROM media_files
        """)
        row = cursor.fetchone()
        conn.close()

        return dict(row)
