import math

def hex_to_rgb(hex_str: str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def srgb_to_linear(c: float) -> float:
    c = c / 255.0
    if c <= 0.03928:
        return c / 12.92
    return math.pow((c + 0.055) / 1.055, 2.4)

def relative_luminance(rgb) -> float:
    r = srgb_to_linear(rgb[0])
    g = srgb_to_linear(rgb[1])
    b = srgb_to_linear(rgb[2])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = relative_luminance(hex_to_rgb(hex1))
    l2 = relative_luminance(hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

TOKENS = {
    "light": {
        "bg": "#FAFAF8",
        "surface": "#FFFFFF",
        "border": "#E6E4DF",
        "text": "#1A1A1A",
        "muted": "#6B6B66",
        "accent": "#0B6B5D",
        "danger": "#B3261E"
    },
    "dark": {
        "bg": "#111113",
        "surface": "#1A1A1D",
        "border": "#2A2A2E",
        "text": "#ECECEC",
        "muted": "#9A9AA0",
        "accent": "#3CB8A2",
        "danger": "#CF6679"
    }
}

def check_all_contrasts():
    print("Checking WCAG AA Contrast Ratios (Target >= 4.5:1 for body text)...")
    passed = True

    for theme, tokens in TOKENS.items():
        print(f"\n[{theme.upper()} THEME]")
        pairs = [
            ("Text on Surface", tokens["text"], tokens["surface"]),
            ("Text on Bg", tokens["text"], tokens["bg"]),
            ("Accent on Surface", tokens["accent"], tokens["surface"]),
            ("White on Accent (Button)", "#FFFFFF", tokens["accent"]),
            ("Danger on Surface", tokens["danger"], tokens["surface"]),
        ]
        for name, c1, c2 in pairs:
            ratio = contrast_ratio(c1, c2)
            ok = ratio >= 4.5
            print(f"  {name:25} ({c1} on {c2}): {ratio:.2f}:1 -> {'PASS' if ok else 'WARN'}")
            if not ok:
                passed = False

    return passed

def test_wcag_contrast():
    for theme, tokens in TOKENS.items():
        text_ratio = contrast_ratio(tokens["text"], tokens["surface"])
        assert text_ratio >= 4.5, f"Text contrast failed on {theme}: {text_ratio:.2f}:1"
        btn_ratio = contrast_ratio("#FFFFFF" if theme=="light" else "#111113", tokens["accent"])
        assert btn_ratio >= 4.0, f"Button text contrast failed on {theme}: {btn_ratio:.2f}:1"

if __name__ == "__main__":
    check_all_contrasts()

