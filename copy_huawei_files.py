#!/usr/bin/env python3
"""复制华为测评相关文件到待整理文件夹"""

import os
import shutil
import time

base = r'L:\sata1-18501755656\HWHBN\HWHBN相册备份'
target = r'L:\sata1-18501755656\华为测评待整理'

def copy_folder(src_name, dest_name, extensions=None):
    """复制文件夹内容"""
    src_path = os.path.join(base, src_name)
    dest_path = os.path.join(target, dest_name)

    if not os.path.exists(src_path):
        print(f'[跳过] {src_name} 不存在')
        return 0, 0

    os.makedirs(dest_path, exist_ok=True)

    count = 0
    size = 0

    for root, dirs, files in os.walk(src_path):
        # 计算相对路径
        rel_path = os.path.relpath(root, src_path)
        if rel_path == '.':
            current_dest = dest_path
        else:
            current_dest = os.path.join(dest_path, rel_path)
            os.makedirs(current_dest, exist_ok=True)

        for f in files:
            # 如果指定了扩展名过滤
            if extensions:
                ext = os.path.splitext(f)[1].lower()
                if ext not in extensions:
                    continue

            src_file = os.path.join(root, f)
            dest_file = os.path.join(current_dest, f)

            try:
                shutil.copy2(src_file, dest_file)
                file_size = os.path.getsize(dest_file)
                count += 1
                size += file_size
                print(f'  + {rel_path}/{f}')
            except Exception as e:
                print(f'  ! {f}: {str(e)}')

    return count, size

def main():
    print('='*60)
    print('华为测评素材整理 - 文件复制工具')
    print('='*60)
    print()

    total_files = 0
    total_size = 0

    # 1. 录屏视频 - 所有 mp4
    print('[1/5] 复制录屏视频...')
    c, s = copy_folder('Screenrecords', '01_录屏视频', {'.mp4'})
    total_files += c
    total_size += s
    print(f'    完成: {c} 个文件, {s/1024/1024:.1f} MB')
    print()

    # 2. 截屏图片 - jpg, png
    print('[2/5] 复制截屏图片...')
    c, s = copy_folder('Screenshots', '02_截屏图片', {'.jpg', '.jpeg', '.png'})
    total_files += c
    total_size += s
    print(f'    完成: {c} 个文件, {s/1024/1024:.1f} MB')
    print()

    # 3. Huawei Share
    print('[3/5] 复制华为分享...')
    c, s = copy_folder('Huawei Share', '03_华为分享')
    total_files += c
    total_size += s
    print(f'    完成: {c} 个文件, {s/1024/1024:.1f} MB')
    print()

    # 4. 小艺
    print('[4/5] 复制小艺...')
    c, s = copy_folder('小艺', '04_小艺')
    total_files += c
    total_size += s
    print(f'    完成: {c} 个文件, {s/1024/1024:.1f} MB')
    print()

    # 5. 小艺服务
    print('[5/5] 复制小艺服务...')
    c, s = copy_folder('小艺服务', '05_小艺服务')
    total_files += c
    total_size += s
    print(f'    完成: {c} 个文件, {s/1024/1024:.1f} MB')
    print()

    print('='*60)
    print(f'复制完成! 共 {total_files} 个文件, 总大小 {total_size/1024/1024:.1f} MB')
    print(f'目标位置: {target}')
    print('='*60)

if __name__ == '__main__':
    main()
