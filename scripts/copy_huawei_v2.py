#!/usr/bin/env python3
"""复制华为测评相关文件到待整理文件夹 - 修复版"""

import os
import shutil

base = r'L:\sata1-18501755656\HWHBN\HWHBN相册备份'
target = r'L:\sata1-18501755656\华为测评待整理'

print(f'源目录: {base}')
print(f'目标目录: {target}')
print()

def copy_all(src, dst, extensions=None):
    """复制所有文件"""
    count = 0
    size = 0
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        dest_dir = dst if rel == '.' else os.path.join(dst, rel)
        os.makedirs(dest_dir, exist_ok=True)
        for f in files:
            if extensions and os.path.splitext(f)[1].lower() not in extensions:
                continue
            try:
                src_file = os.path.join(root, f)
                dst_file = os.path.join(dest_dir, f)
                shutil.copy2(src_file, dst_file)
                count += 1
                size += os.path.getsize(dst_file)
            except Exception as e:
                print(f'  ! {f}: {e}')
    return count, size

# 列出所有文件夹
print('源文件夹列表:')
items = os.listdir(base)
for item in items:
    path = os.path.join(base, item)
    if os.path.isdir(path):
        print(f'  [DIR] {item}')
    else:
        print(f'  [FILE] {item}')
print()

# 1. Screenrecords
print('[1] 复制 Screenrecords (录屏视频)...')
src = os.path.join(base, 'Screenrecords')
dst = os.path.join(target, '01_录屏视频')
c, s = copy_all(src, dst, {'.mp4'})
print(f'  完成: {c} 个文件, {s/1024/1024:.1f} MB')
print()

# 2. Screenshots
print('[2] 复制 Screenshots (截屏图片)...')
src = os.path.join(base, 'Screenshots')
dst = os.path.join(target, '02_截屏图片')
c, s = copy_all(src, dst, {'.jpg', '.jpeg', '.png'})
print(f'  完成: {c} 个文件, {s/1024/1024:.1f} MB')
print()

# 3. Huawei Share
print('[3] 复制 Huawei Share...')
src = os.path.join(base, 'Huawei Share')
dst = os.path.join(target, '03_华为分享')
os.makedirs(dst, exist_ok=True)
c, s = 0, 0
for f in os.listdir(src):
    if os.path.isfile(os.path.join(src, f)):
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        c += 1
        s += os.path.getsize(os.path.join(dst, f))
print(f'  完成: {c} 个文件, {s/1024/1024:.1f} MB')
print()

# 4. 小艺相关
小艺_folder = None
小艺服务_folder = None
for item in os.listdir(base):
    if '小艺' in item and os.path.isdir(os.path.join(base, item)):
        if '服务' in item:
            小艺服务_folder = item
        else:
            小艺_folder = item

if 小艺_folder:
    print('[4] 复制小艺...')
    src = os.path.join(base, 小艺_folder)
    dst = os.path.join(target, '04_小艺')
    os.makedirs(dst, exist_ok=True)
    c, s = 0, 0
    for f in os.listdir(src):
        if os.path.isfile(os.path.join(src, f)):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
            c += 1
            s += os.path.getsize(os.path.join(dst, f))
    print(f'  完成: {c} 个文件, {s/1024/1024:.1f} MB')
    print()

if 小艺服务_folder:
    print('[5] 复制小艺服务...')
    src = os.path.join(base, 小艺服务_folder)
    dst = os.path.join(target, '05_小艺服务')
    os.makedirs(dst, exist_ok=True)
    c, s = 0, 0
    for f in os.listdir(src):
        if os.path.isfile(os.path.join(src, f)):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
            c += 1
            s += os.path.getsize(os.path.join(dst, f))
    print(f'  完成: {c} 个文件, {s/1024/1024:.1f} MB')
    print()

print('='*60)
print('复制完成!')
print('='*60)
