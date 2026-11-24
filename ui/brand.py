"""
Brand mark — «حاضر | Hader»

An open-cornered scan frame with a check mark completing inside it.
The same drawing is used for the app header, the "attendance recorded"
state, and (via draw_scan_frame_cv) the overlay on the live camera.
"""

from PIL import Image, ImageDraw

# Geometry in a unit square (0..1)
_CORNER_LEN = 0.30
_FRAME_STROKE = 0.085
_CHECK_POINTS = [(0.29, 0.53), (0.44, 0.67), (0.72, 0.36)]
_CHECK_STROKE = 0.10


def _hex_rgba(color, alpha=255):
    if isinstance(color, tuple):
        return color if len(color) == 4 else color + (alpha,)
    h = color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def _partial_polyline(points, progress):
    """Return the polyline truncated to `progress` (0..1) of its length."""
    if progress >= 1:
        return points
    segs = list(zip(points, points[1:]))
    lengths = [((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in segs]
    target = sum(lengths) * max(0.0, progress)
    out = [points[0]]
    for (a, b), ln in zip(segs, lengths):
        if target >= ln:
            out.append(b)
            target -= ln
        else:
            t = target / ln if ln else 0
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            break
    return out


def draw_mark(size, frame_color, check_color=None, check_progress=1.0, background=None):
    """Brand mark as a PIL RGBA image (drawn 4x and downsampled for smooth edges)."""
    ss = 4
    S = size * ss
    img = Image.new("RGBA", (S, S), _hex_rgba(background) if background else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fw = max(2, int(S * _FRAME_STROKE))
    pad = fw / 2 + S * 0.04
    L = S * _CORNER_LEN
    fc = _hex_rgba(frame_color)
    x0, y0, x1, y1 = pad, pad, S - pad, S - pad
    corners = [
        [(x0, y0 + L), (x0, y0), (x0 + L, y0)],
        [(x1 - L, y0), (x1, y0), (x1, y0 + L)],
        [(x1, y1 - L), (x1, y1), (x1 - L, y1)],
        [(x0 + L, y1), (x0, y1), (x0, y1 - L)],
    ]
    for pts in corners:
        d.line(pts, fill=fc, width=fw, joint="curve")
        for p in (pts[0], pts[-1]):
            d.ellipse((p[0] - fw / 2, p[1] - fw / 2, p[0] + fw / 2, p[1] + fw / 2), fill=fc)

    if check_progress > 0:
        cc = _hex_rgba(check_color or frame_color)
        cw = max(2, int(S * _CHECK_STROKE))
        pts = [(x * S, y * S) for x, y in _CHECK_POINTS]
        pts = _partial_polyline(pts, check_progress)
        if len(pts) > 1:
            d.line(pts, fill=cc, width=cw, joint="curve")
        for p in (pts[0], pts[-1]):
            d.ellipse((p[0] - cw / 2, p[1] - cw / 2, p[0] + cw / 2, p[1] + cw / 2), fill=cc)
    return img.resize((size, size), Image.LANCZOS)


def mark_ctk(size, frame_color, check_color=None, check_progress=1.0):
    import customtkinter
    img = draw_mark(size, frame_color, check_color, check_progress)
    return customtkinter.CTkImage(light_image=img, dark_image=img, size=(size, size))


def draw_scan_frame_cv(frame, box, color_bgr, thickness=3, check=False, check_progress=1.0):
    """
    Draw the same open-cornered frame around a face on an OpenCV frame,
    optionally completing the check mark inside it (used on success).
    box = (x, y, w, h)
    """
    import cv2
    x, y, w, h = [int(v) for v in box]
    pad = int(0.12 * max(w, h))
    x0, y0, x1, y1 = x - pad, y - pad, x + w + pad, y + h + pad
    L = int(0.26 * (x1 - x0))
    for (ax, ay), (bx, by), (cx, cy) in [
        ((x0, y0 + L), (x0, y0), (x0 + L, y0)),
        ((x1 - L, y0), (x1, y0), (x1, y0 + L)),
        ((x1, y1 - L), (x1, y1), (x1 - L, y1)),
        ((x0 + L, y1), (x0, y1), (x0, y1 - L)),
    ]:
        cv2.line(frame, (ax, ay), (bx, by), color_bgr, thickness, cv2.LINE_AA)
        cv2.line(frame, (bx, by), (cx, cy), color_bgr, thickness, cv2.LINE_AA)
    if check:
        W, H = x1 - x0, y1 - y0
        pts = [(x0 + px * W, y0 + py * H) for px, py in _CHECK_POINTS]
        pts = _partial_polyline(pts, check_progress)
        for a, b in zip(pts, pts[1:]):
            cv2.line(frame, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), color_bgr,
                     max(3, thickness + 2), cv2.LINE_AA)
    return frame


if __name__ == "__main__":
    # Writes the mark as PNG files, e.g. for the README.
    import os
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/images"
    os.makedirs(out, exist_ok=True)
    draw_mark(512, "#0E5E6F").save(os.path.join(out, "hader-mark.png"))
    draw_mark(512, "#1D7A4C").save(os.path.join(out, "hader-mark-success.png"))
    print("written to", out)
