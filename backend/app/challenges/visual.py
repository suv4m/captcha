import io
import math
import base64
import random
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw

SHAPES = ["circle", "triangle", "square", "star", "hexagon", "cross"]

COLORS = [
    (30, 30, 30),
    (20, 80, 160),
    (180, 40, 40),
    (30, 140, 80),
    (140, 60, 160),
    (180, 100, 20),
]


def _draw_shape(draw: ImageDraw.ImageDraw, shape: str, cx: float, cy: float,
                r: float, rotation_deg: float, fill_color: Tuple[int, int, int]):
    rad = math.radians(rotation_deg)

    if shape == "circle":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill_color, outline=(0, 0, 0), width=2)

    elif shape == "square":
        pts = []
        for a in [45, 135, 225, 315]:
            ang = math.radians(a + rotation_deg)
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        draw.polygon(pts, fill=fill_color, outline=(0, 0, 0), width=2)

    elif shape == "triangle":
        pts = []
        for a in [90, 210, 330]:
            ang = math.radians(a + rotation_deg)
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        draw.polygon(pts, fill=fill_color, outline=(0, 0, 0), width=2)

    elif shape == "hexagon":
        pts = []
        for i in range(6):
            ang = math.radians(i * 60 + rotation_deg)
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        draw.polygon(pts, fill=fill_color, outline=(0, 0, 0), width=2)

    elif shape == "star":
        pts = []
        for i in range(10):
            dist = r if (i % 2 == 0) else (r * 0.45)
            ang = math.radians(i * 36 - 90 + rotation_deg)
            pts.append((cx + dist * math.cos(ang), cy + dist * math.sin(ang)))
        draw.polygon(pts, fill=fill_color, outline=(0, 0, 0), width=2)

    elif shape == "cross":
        # Plus / cross shape
        w = r * 0.35
        # Draw two intersecting thick rectangles
        pts1 = [
            (cx - w, cy - r), (cx + w, cy - r),
            (cx + w, cy + r), (cx - w, cy + r)
        ]
        pts2 = [
            (cx - r, cy - w), (cx + r, cy - w),
            (cx + r, cy + w), (cx - r, cy + w)
        ]
        # Rotate points
        def rot(pt):
            dx = pt[0] - cx
            dy = pt[1] - cy
            return (cx + dx * math.cos(rad) - dy * math.sin(rad),
                    cy + dx * math.sin(rad) + dy * math.cos(rad))
        draw.polygon([rot(p) for p in pts1], fill=fill_color, outline=(0, 0, 0), width=1)
        draw.polygon([rot(p) for p in pts2], fill=fill_color, outline=(0, 0, 0), width=1)


def _render_tile(shape: str, level: int, rng: random.Random) -> str:
    size = 120
    img = Image.new("RGB", (size, size), color=(rng.randint(235, 250), rng.randint(235, 250), rng.randint(235, 250)))
    draw = ImageDraw.Draw(img)

    # Distractor noise scaling with level
    num_lines = {1: 3, 2: 8, 3: 16}.get(level, 6)
    for _ in range(num_lines):
        x1, y1 = rng.randint(0, size), rng.randint(0, size)
        x2, y2 = rng.randint(0, size), rng.randint(0, size)
        lcolor = (rng.randint(180, 220), rng.randint(180, 220), rng.randint(180, 220))
        draw.line([x1, y1, x2, y2], fill=lcolor, width=rng.randint(1, 2))

    # Main shape
    cx = size / 2.0 + rng.uniform(-6.0, 6.0)
    cy = size / 2.0 + rng.uniform(-6.0, 6.0)
    radius = rng.uniform(30.0, 42.0)
    rotation = rng.uniform(0.0, 360.0)
    color = rng.choice(COLORS)
    _draw_shape(draw, shape, cx, cy, radius, rotation, color)

    # Add extra random salt/pepper dots for level 2 and 3
    if level >= 2:
        num_dots = 40 if level == 2 else 90
        for _ in range(num_dots):
            dx = rng.randint(0, size - 1)
            dy = rng.randint(0, size - 1)
            img.putpixel((dx, dy), (rng.randint(50, 200), rng.randint(50, 200), rng.randint(50, 200)))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def create(level: int = 1, rng: random.Random = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if rng is None:
        rng = random.Random()

    target_shape = rng.choice(SHAPES)
    target_count = rng.randint(2, 4)
    target_indices = sorted(rng.sample(range(9), target_count))

    other_shapes = [s for s in SHAPES if s != target_shape]
    tiles = []

    for i in range(9):
        if i in target_indices:
            tile_shape = target_shape
        else:
            tile_shape = rng.choice(other_shapes)
        tile_data_uri = _render_tile(tile_shape, level, rng)
        tiles.append(tile_data_uri)

    public = {
        "type": "visual",
        "level": level,
        "prompt": f"Select every tile containing a {target_shape}.",
        "target_shape": target_shape,
        "grid_size": 3,
        "tiles": tiles
    }
    secret = {
        "target_indices": target_indices
    }
    return public, secret


def verify(secret: Dict[str, Any], answer: Any, interaction: Dict[str, Any] = None) -> bool:
    if not isinstance(answer, (list, tuple)):
        return False
    try:
        user_selection = sorted([int(x) for x in answer])
        return user_selection == sorted(secret["target_indices"])
    except (ValueError, TypeError):
        return False

