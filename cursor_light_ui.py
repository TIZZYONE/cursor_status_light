"""红绿灯视觉样式：PIL 绘制，与状态逻辑、窗口逻辑分离。"""

from __future__ import annotations

from PIL import Image, ImageDraw

BASE_W, BASE_H = 96, 252
RENDER_SCALE = 3
CHROMA = (1, 1, 1)

LAMP = {
    "red_on": (238, 48, 42),
    "red_off": (60, 32, 32),
    "yellow_on": (255, 208, 48),
    "yellow_off": (54, 50, 28),
    "green_on": (42, 218, 88),
    "green_off": (30, 54, 38),
}

GLOW = {
    "red": (255, 60, 50),
    "yellow": (255, 210, 60),
    "green": (50, 230, 100),
}


def rgba_to_chroma(rgba: Image.Image) -> Image.Image:
    bg = Image.new("RGB", rgba.size, CHROMA)
    bg.paste(rgba, mask=rgba.split()[3])
    return bg


def _draw_ground_shadow(draw: ImageDraw.ImageDraw, cx: int, cy: int, s: int) -> None:
    """单层灰色落地椭圆，无描边。"""
    rx, ry = int(28 * s), int(6 * s)
    draw.ellipse(
        (cx - rx, cy - ry, cx + rx, cy + ry),
        fill=(196, 196, 200, 255),
    )


def _draw_pole(draw: ImageDraw.ImageDraw, cx: int, y1: int, y2: int, s: int) -> None:
    """细灯柱，纯色无描边。"""
    w = max(2, int(3 * s))
    draw.rectangle((cx - w, y1, cx + w, y2), fill=(110, 110, 114, 255))


def _draw_pole_foot(draw: ImageDraw.ImageDraw, cx: int, y: int, s: int) -> None:
    """柱脚小圆点，与灯柱同色。"""
    r = max(2, int(3 * s))
    draw.ellipse((cx - r, y - r, cx + r, y + r), fill=(110, 110, 114, 255))


def _draw_housing(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, s: int) -> None:
    draw.rounded_rectangle((x1, y1, x2, y2), radius=int(6 * s), fill=(22, 22, 24, 255))
    draw.rounded_rectangle(
        (x1 + s, y1 + s, x2 - s, y2 - s),
        radius=int(5 * s),
        outline=(58, 58, 62, 255),
        width=max(1, s),
    )
    draw.line(
        (x1 + int(3 * s), y1 + int(6 * s), x1 + int(3 * s), y2 - int(6 * s)),
        fill=(70, 70, 74, 90),
        width=max(1, s),
    )


def _draw_section_divider(draw: ImageDraw.ImageDraw, x1: int, x2: int, y: int, s: int) -> None:
    draw.line((x1 + int(4 * s), y, x2 - int(4 * s), y), fill=(12, 12, 14, 255), width=max(1, s))
    draw.line((x1 + int(4 * s), y + s, x2 - int(4 * s), y + s), fill=(45, 45, 48, 180), width=max(1, s))


def _draw_visor(draw: ImageDraw.ImageDraw, x1: int, x2: int, y: int, s: int) -> None:
    h = int(8 * s)
    draw.rounded_rectangle(
        (x1 + int(8 * s), y - h, x2 - int(8 * s), y + int(2 * s)),
        radius=int(3 * s),
        fill=(16, 16, 18, 255),
    )


def _draw_screw(draw: ImageDraw.ImageDraw, x: int, y: int, s: int) -> None:
    r = max(1, int(1.6 * s))
    draw.ellipse((x - r, y - r, x + r, y + r), fill=(48, 48, 52, 255))


def _draw_lamp(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    on: bool,
    on_rgb: tuple[int, int, int],
    off_rgb: tuple[int, int, int],
    glow_rgb: tuple[int, int, int],
    s: int,
) -> None:
    if on:
        draw.ellipse(
            (cx - r - int(6 * s), cy - r - int(6 * s), cx + r + int(6 * s), cy + r + int(6 * s)),
            fill=(*glow_rgb, 40),
        )
    bezel = (18, 18, 20, 255) if on else (14, 14, 16, 255)
    draw.ellipse((cx - r - s, cy - r - s, cx + r + s, cy + r + s), fill=bezel)
    rgb = on_rgb if on else off_rgb
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*rgb, 255))
    if on:
        step = max(3, r // 3)
        for i in range(-r, r, step):
            draw.line((cx + i, cy - r, cx + i, cy + r), fill=(255, 255, 255, 10), width=1)
            draw.line((cx - r, cy + i, cx + r, cy + i), fill=(255, 255, 255, 10), width=1)
        hr = max(4, r // 2)
        draw.ellipse(
            (cx - r // 2 - hr // 2, cy - r // 2 - hr // 2, cx - r // 2 + hr // 2, cy - r // 2 + hr // 2),
            fill=(255, 255, 255, 150),
        )
    else:
        draw.ellipse((cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2), fill=(*off_rgb, 180))


def lamp_states_for_agg(agg: str) -> tuple[bool, bool, bool]:
    if agg == "error":
        return True, False, False
    if agg == "busy":
        return False, True, False
    return False, False, True


def render_traffic_light(agg: str, scale: int) -> Image.Image:
    s = scale
    w, h = BASE_W * s, BASE_H * s
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w // 2

    shadow_cy = int(240 * s)
    pole_bottom = shadow_cy - int(2 * s)
    _draw_ground_shadow(draw, cx, shadow_cy, s)
    _draw_pole(draw, cx, int(118 * s), pole_bottom, s)
    _draw_pole_foot(draw, cx, pole_bottom, s)

    hx1, hy1 = int(22 * s), int(10 * s)
    hx2, hy2 = int(74 * s), int(118 * s)
    _draw_housing(draw, hx1, hy1, hx2, hy2, s)

    section_h = (hy2 - hy1) // 3
    for i in range(1, 3):
        _draw_section_divider(draw, hx1, hx2, hy1 + section_h * i, s)

    r = int(15 * s)
    lamp_ys = [
        hy1 + section_h // 2,
        hy1 + section_h + section_h // 2,
        hy1 + 2 * section_h + section_h // 2,
    ]
    visor_ys = [hy1 + int(4 * s), hy1 + section_h + int(4 * s), hy1 + 2 * section_h + int(4 * s)]

    red_on, yellow_on, green_on = lamp_states_for_agg(agg)
    lamp_defs = (
        (red_on, LAMP["red_on"], LAMP["red_off"], GLOW["red"]),
        (yellow_on, LAMP["yellow_on"], LAMP["yellow_off"], GLOW["yellow"]),
        (green_on, LAMP["green_on"], LAMP["green_off"], GLOW["green"]),
    )

    for i, (on, on_c, off_c, glow_c) in enumerate(lamp_defs):
        _draw_visor(draw, hx1 + int(6 * s), hx2 - int(6 * s), visor_ys[i], s)
        _draw_lamp(draw, cx, lamp_ys[i], r, on, on_c, off_c, glow_c, s)
        margin = int(8 * s)
        _draw_screw(draw, hx1 + margin, hy1 + section_h * i + int(6 * s), s)
        _draw_screw(draw, hx2 - margin, hy1 + section_h * i + int(6 * s), s)
        _draw_screw(draw, hx1 + margin, hy1 + section_h * (i + 1) - int(6 * s), s)
        _draw_screw(draw, hx2 - margin, hy1 + section_h * (i + 1) - int(6 * s), s)

    return rgba_to_chroma(img)


def make_tray_icon_image(agg: str = "success") -> Image.Image:
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 2, 28, 30), radius=4, fill=(30, 30, 32))
    color_map = {
        "error": [(255, 60, 55), (50, 50, 54), (50, 50, 54)],
        "busy": [(50, 50, 54), (255, 208, 48), (50, 50, 54)],
        "success": [(50, 50, 54), (50, 50, 54), (42, 218, 88)],
    }
    colors = color_map.get(agg, color_map["success"])
    for (x1, y1, x2, y2), col in zip([(13, 6, 19, 12), (13, 13, 19, 19), (13, 20, 19, 26)], colors):
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        r = (x2 - x1) // 2
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    return im
