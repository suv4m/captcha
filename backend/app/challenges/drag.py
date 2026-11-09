import io
import math
import base64
import random
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter


def _generate_textured_bg(w: int, h: int, rng: random.Random) -> Image.Image:
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    # Base gradient
    c1 = (rng.randint(40, 100), rng.randint(60, 120), rng.randint(80, 140))
    c2 = (rng.randint(120, 190), rng.randint(100, 170), rng.randint(60, 130))

    for y in range(h):
        ratio = y / float(h)
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Add geometric shapes / texture
    for _ in range(12):
        x1 = rng.randint(0, w)
        y1 = rng.randint(0, h)
        rad = rng.randint(20, 80)
        color = (rng.randint(50, 220), rng.randint(50, 220), rng.randint(50, 220))
        draw.ellipse([x1 - rad, y1 - rad, x1 + rad, y1 + rad], fill=None, outline=color, width=rng.randint(2, 5))

    for _ in range(8):
        x1, y1 = rng.randint(0, w), rng.randint(0, h)
        x2, y2 = rng.randint(0, w), rng.randint(0, h)
        draw.line([x1, y1, x2, y2], fill=(240, 240, 240), width=rng.randint(1, 3))

    return img


def create(level: int = 1, rng: random.Random = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if rng is None:
        rng = random.Random()

    bg_w, bg_h = 320, 160
    piece_size = 50

    bg = _generate_textured_bg(bg_w, bg_h, rng)

    # Position for target puzzle hole
    hole_x = rng.randint(70, bg_w - piece_size - 20)
    hole_y = rng.randint(20, bg_h - piece_size - 20)

    # Crop piece from intact background before cutting hole
    piece = bg.crop((hole_x, hole_y, hole_x + piece_size, hole_y + piece_size))

    # Add shadow/border to piece
    piece_draw = ImageDraw.Draw(piece)
    piece_draw.rectangle([0, 0, piece_size - 1, piece_size - 1], outline=(255, 255, 255), width=2)

    # Render hole in background
    bg_draw = ImageDraw.Draw(bg)
    # Darkened hole
    bg_draw.rectangle(
        [hole_x, hole_y, hole_x + piece_size, hole_y + piece_size],
        fill=(30, 30, 35), outline=(20, 20, 20), width=2
    )

    # Level 3 decoy holes
    if level >= 3:
        decoy_x = rng.randint(20, 100)
        if abs(decoy_x - hole_x) > 60:
            bg_draw.rectangle(
                [decoy_x, hole_y, decoy_x + piece_size, hole_y + piece_size],
                fill=(45, 45, 50), outline=(25, 25, 25), width=2
            )

    tolerance_map = {1: 9, 2: 6, 3: 4}
    tolerance = tolerance_map.get(level, 6)

    # Convert to base64
    bg_buf = io.BytesIO()
    bg.save(bg_buf, format="PNG")
    bg_b64 = f"data:image/png;base64,{base64.b64encode(bg_buf.getvalue()).decode('utf-8')}"

    piece_buf = io.BytesIO()
    piece.save(piece_buf, format="PNG")
    piece_b64 = f"data:image/png;base64,{base64.b64encode(piece_buf.getvalue()).decode('utf-8')}"

    public = {
        "type": "drag",
        "level": level,
        "prompt": "Drag the slider to fit the puzzle piece into the target hole.",
        "bg_image": bg_b64,
        "piece_image": piece_b64,
        "bg_width": bg_w,
        "bg_height": bg_h,
        "piece_size": piece_size,
        "piece_y": hole_y
    }
    secret = {
        "hole_x": hole_x,
        "tolerance": tolerance
    }
    return public, secret


def verify(secret: Dict[str, Any], answer: Any, interaction: Dict[str, Any] = None) -> bool:
    try:
        if isinstance(answer, dict):
            user_x = float(answer.get("x", answer.get("position", -100)))
        else:
            user_x = float(answer)

        hole_x = float(secret["hole_x"])
        tol = float(secret["tolerance"])
        return abs(user_x - hole_x) <= tol
    except (ValueError, TypeError):
        return False

