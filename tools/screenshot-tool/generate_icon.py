"""生成卡通风格截图工具图标 (256x256 多尺寸 .ico)"""
from PIL import Image, ImageDraw, ImageFilter
import os, math

OUT = os.path.join(os.path.dirname(__file__), "app.ico")
SZ = 256

img = Image.new("RGBA", (SZ, SZ), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# ── 色彩 ──────────────────────────────
BG_TOP    = (52,  199, 255)   # 亮青
BG_BOTTOM = (0,   122, 255)   # 蓝
LENS_OUT  = (255, 255, 255)   # 镜头外圈
LENS_IN   = (40,  180, 255)   # 镜头内圈
SHINE     = (255, 255, 255, 180)
SHADOW    = (0,   0,   0,   40)
BORDER    = (255, 255, 255)

# ── 主体圆角矩形 ───────────────────────
body = (30, 50, SZ - 30, SZ - 30)
r = 36

# 阴影
d.rounded_rectangle([x + 4 for x in body[:2]] + [x + 4 for x in body[2:]], radius=r, fill=SHADOW)
# 主体渐变
for i in range(body[1], body[3]):
    t = (i - body[1]) / (body[3] - body[1])
    cr = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
    cg = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
    cb = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
    d.rounded_rectangle([body[0], i, body[2], i + 1], radius=r, fill=(cr, cg, cb))

# ── 顶部闪光条 ────────────────────────
shine_rect = [body[0] + 20, body[1] + 10, body[2] - 20, body[1] + SZ // 3]
d.rounded_rectangle(shine_rect, radius=20, fill=SHINE)

# ── 镜头（大圆） ──────────────────────
cx, cy = SZ // 2, SZ // 2
lens_r = 64

# 外圈白
d.ellipse([cx - lens_r, cy - lens_r, cx + lens_r, cy + lens_r], fill=LENS_OUT)
# 内圈蓝
inner_r = lens_r - 8
d.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=LENS_IN)
# 镜头高光
hl_r = inner_r - 14
d.ellipse([cx - hl_r, cy - hl_r - 10, cx + hl_r, cy + hl_r - 10], fill=SHINE)
# 瞳孔
p_r = 16
d.ellipse([cx - p_r, cy - p_r, cx + p_r, cy + p_r], fill=(18, 60, 130))
# 瞳孔高光
d.ellipse([cx + 4, cy - 8, cx + 14, cy + 2], fill=(255, 255, 255, 220))

# ── 取景框四角 ────────────────────────
corner_sz, corner_w = 28, 6
corners = [
    (body[0] + 16, body[1] + 16),  # 左上
    (body[2] - 16 - corner_sz, body[1] + 16),  # 右上
    (body[0] + 16, body[3] - 16 - corner_sz),  # 左下
    (body[2] - 16 - corner_sz, body[3] - 16 - corner_sz),  # 右下
]
for ox, oy in corners:
    # 横线
    d.rounded_rectangle([ox, oy, ox + corner_sz, oy + corner_w], radius=3, fill=BORDER)
    # 竖线
    d.rounded_rectangle([ox, oy, ox + corner_w, oy + corner_sz], radius=3, fill=BORDER)

# ── 保存到多尺寸 ico ──────────────────
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
imgs = [img.resize(s, Image.LANCZOS) for s in sizes]
imgs[0].save(OUT, format="ICO", sizes=[(s[0], s[1]) for s in sizes], append_images=imgs[1:])
print(f"Icon saved: {OUT}")
