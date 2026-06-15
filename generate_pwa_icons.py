"""生成绘梨衣 PWA 灯笼图标 — 192x192 + 512x512"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import math

ICON_DIR = Path(__file__).parent / "icons"
ICON_DIR.mkdir(exist_ok=True)

LANTERN_RED = (232, 84, 62)       # #E8543E
LANTERN_RED_DARK = (200, 60, 42)
GLOW_WARM = (255, 128, 80, 80)
GLOW_GOLD = (255, 180, 100, 60)
CORE_YELLOW = (255, 200, 130)


def draw_lantern(size: int) -> Image.Image:
    """绘制灯笼图标，保存为 PNG"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx = cy = size / 2
    r = int(size * 0.18)  # 主体半径

    # ── 4层光晕 (外→内) ──
    halos = [
        (int(r * 2.5), (224, 100, 80, 25)),
        (int(r * 1.85), (232, 84, 62, 50)),
        (int(r * 1.45), (240, 120, 90, 45)),
        (int(r * 1.15), (245, 150, 110, 40)),
    ]
    for hr, hcolor in halos:
        halo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        hdraw = ImageDraw.Draw(halo)
        hdraw.ellipse(
            [cx - hr, cy - hr, cx + hr, cy + hr],
            fill=hcolor,
        )
        halo = halo.filter(ImageFilter.GaussianBlur(radius=hr * 0.35))
        img = Image.alpha_composite(img, halo)

    # ── 主体红圆 ──
    main_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mdraw = ImageDraw.Draw(main_layer)
    mdraw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=LANTERN_RED,
    )
    # 主体内光晕
    inner_glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    idraw = ImageDraw.Draw(inner_glow)
    ir = int(r * 0.75)
    idraw.ellipse(
        [cx - ir, cy - ir, cx + ir, cy + ir],
        fill=(255, 140, 100, 60),
    )
    inner_glow = inner_glow.filter(ImageFilter.GaussianBlur(radius=ir * 0.3))
    main_layer = Image.alpha_composite(main_layer, inner_glow)
    img = Image.alpha_composite(img, main_layer)

    # ── 光核 ──
    core_r = int(r * 0.28)
    core_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(core_layer)
    cdraw.ellipse(
        [cx - core_r, cy - core_r, cx + core_r, cy + core_r],
        fill=CORE_YELLOW,
    )
    core_layer = core_layer.filter(ImageFilter.GaussianBlur(radius=core_r * 0.5))
    img = Image.alpha_composite(img, core_layer)

    # ── 两点高光 ──
    highlight_r = int(r * 0.12)
    for hx_off in [-r * 0.35, r * 0.35]:
        hl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        hldraw = ImageDraw.Draw(hl)
        hx = int(cx + hx_off)
        hy = int(cy - r * 0.3)
        hldraw.ellipse(
            [hx - highlight_r, hy - highlight_r, hx + highlight_r, hy + highlight_r],
            fill=(255, 255, 255, 200),
        )
        hl = hl.filter(ImageFilter.GaussianBlur(radius=highlight_r * 0.6))
        img = Image.alpha_composite(img, hl)

    return img


if __name__ == "__main__":
    for size in [192, 512]:
        icon = draw_lantern(size)
        path = ICON_DIR / f"icon-{size}.png"
        icon.save(path, "PNG")
        fs = path.stat().st_size
        print(f"  icon-{size}.png  {size}x{size}  ({fs / 1024:.1f} KB)")
    print()
    print("PWA 图标就绪 → manifest.json 可引用")
