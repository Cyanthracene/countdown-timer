"""生成倒计时器图标 timer-icon.ico

关键点：ICO 里 256 以下的帧必须是传统 BMP/DIB 格式。Pillow 的 ICO 保存器
会把所有尺寸都写成 PNG，Windows 解析「快捷方式图标」时会失败并回退成通用
文件图标，所以这里手写 ICO 容器。

依赖: pillow, numpy     用法: python make_icon.py
"""
import io
import math
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 1024
OUT_DIR = r"C:\Users\Cyanthracene\Documents\deepseek-harness\default-workspace\countdown-timer"
STOPS = [(0.0, (45, 212, 191)), (0.5, (56, 132, 246)), (1.0, (139, 92, 246))]  # 青 -> 蓝 -> 紫
SIZES = [16, 24, 32, 48, 64, 128, 256]


def background():
    """对角渐变 + 左上高光 + 底部内阴影 + 圆角遮罩"""
    ys, xs = np.mgrid[0:S, 0:S].astype(np.float32)
    t = (xs + ys) / (2 * (S - 1))
    c0, c1, c2 = (np.array(c, np.float32) for _, c in STOPS)
    seg1 = c0 + (c1 - c0) * np.clip(t[..., None] / 0.5, 0, 1)
    seg2 = c1 + (c2 - c1) * np.clip((t[..., None] - 0.5) / 0.5, 0, 1)
    c = np.where((t <= 0.5)[..., None], seg1, seg2)

    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    d = np.sqrt(((xx - 0.30 * S) / (0.95 * S)) ** 2 + (yy / (0.80 * S)) ** 2)
    hl = np.clip(1 - d, 0, 1) ** 2.2 * 0.30
    c = c * (1 - hl[..., None]) + 255.0 * hl[..., None]

    sh = np.clip((yy / S - 0.52) / 0.48, 0, 1) ** 2 * 0.18
    c = c * (1 - sh[..., None])

    img = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=232, fill=255)
    img.putalpha(mask)
    return img


def pt(cx, cy, ang, r):
    a = math.radians(ang)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def dial(d, cx, cy, R, w, sweep, hand1, hand2, hand_w, hub, track_a, color):
    """表盘：底环 + 进度弧 + 两根指针 + 轴心"""
    box = [cx - R, cy - R, cx + R, cy + R]
    d.ellipse(box, outline=color[:3] + (track_a,), width=w)
    a0, a1 = 270.0, 270.0 + sweep
    d.arc(box, a0, a1, fill=color, width=w)
    for ang in (a0, a1):  # 圆头端点
        x, y = pt(cx, cy, ang, R)
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=color)
    for ang, length in ((270.0, hand1), (38.0, hand2)):
        ex, ey = pt(cx, cy, ang, length)
        d.line([(cx, cy), (ex, ey)], fill=color, width=hand_w)
        d.ellipse([ex - hand_w / 2, ey - hand_w / 2, ex + hand_w / 2, ey + hand_w / 2], fill=color)
    d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=color)


def render_master():
    cx, cy, R, w = 512, 520, 296, 86
    kw = dict(sweep=280, hand1=116, hand2=132, hand_w=48, hub=46, track_a=52)
    img = background()
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dial(ImageDraw.Draw(shadow), cx, cy + 12, R, w, color=(14, 26, 70, 70), **kw)
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(22)))
    dial(ImageDraw.Draw(img), cx, cy, R, w, color=(255, 255, 255, 255), **kw)
    return img


def bmp_frame(img):
    """把 RGBA 方图编码成 ICO 内的传统 BMP 帧（BITMAPINFOHEADER + BGRA + AND 掩码）"""
    w, h = img.size
    px = img.load()
    rows = []
    for y in range(h - 1, -1, -1):          # DIB 自下而上
        row = bytearray()
        for x in range(w):
            r, g, b, a = px[x, y]
            row += bytes((b, g, r, a))      # BGRA
        rows.append(bytes(row))
    xor = b"".join(rows)

    stride = ((w + 31) // 32) * 4           # 1bpp 行按 4 字节对齐
    mrows = []
    for y in range(h - 1, -1, -1):
        bits = bytearray(stride)
        for x in range(w):
            if px[x, y][3] < 128:           # 1 = 透明
                bits[x >> 3] |= 0x80 >> (x & 7)
        mrows.append(bytes(bits))
    mask = b"".join(mrows)

    header = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0,
                         len(xor) + len(mask), 0, 0, 0, 0)
    return header + xor + mask


def png_frame(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def write_ico(master, path):
    frames = []
    for size in SIZES:
        im = master if size == S else master.resize((size, size), Image.LANCZOS)
        # 256 用 PNG（Windows 唯一官方支持 PNG 的尺寸），其余必须是 BMP
        frames.append((size, png_frame(im) if size >= 256 else bmp_frame(im)))
    n = len(frames)
    offset = 6 + 16 * n
    dirents, blob = b"", b""
    for size, data in frames:
        b = 0 if size >= 256 else size
        dirents += struct.pack("<BBBBHHII", b, b, 0, 0, 1, 32, len(data), offset + len(blob))
        blob += data
    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, n) + dirents + blob)
    return len(blob) + offset


def main():
    master = render_master()
    ico = f"{OUT_DIR}\\timer-icon.ico"
    total = write_ico(master, ico)
    master.resize((256, 256), Image.LANCZOS).save(f"{OUT_DIR}\\icon-preview.png")
    print(f"written: {ico}  ({total} bytes)")


if __name__ == "__main__":
    main()
