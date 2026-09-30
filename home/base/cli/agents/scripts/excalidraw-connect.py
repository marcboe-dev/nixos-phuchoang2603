"""Draw orthogonal (elbow) arrows between Excalidraw canvas elements."""

import argparse
import json
import os
import secrets
import sys
import urllib.error
import urllib.request

GAP = 8
STUB = 30
SIDES = {
    "right": (1, 0),
    "left": (-1, 0),
    "top": (0, -1),
    "bottom": (0, 1),
}


def fail(msg, code=1):
    print(json.dumps({"success": False, "error": msg}), file=sys.stderr)
    sys.exit(code)


def http(url, data=None, method=None):
    headers = {"User-Agent": "excalidraw-connect/1.0"}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code} {e.reason} for {url}: {e.read().decode()[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"cannot reach {url}: {e.reason}") from e


def bbox(el, elements):
    """Element bbox; icon labels (<id>-label below the icon) extend the bottom
    so arrows leaving downward don't cut through the label."""
    x, y = el["x"], el["y"]
    w, h = el.get("width") or 0, el.get("height") or 0
    box = {"x0": x, "y0": y, "x1": x + w, "y1": y + h, "w": w, "h": h}
    label = elements.get(f"{el['id']}-label")
    if label and el.get("type") == "image":
        lh = label.get("height") or 20
        box["y1b"] = max(box["y1"], label["y"] + lh)
    else:
        box["y1b"] = box["y1"]
    return box


def auto_sides(a, b):
    acx, acy = (a["x0"] + a["x1"]) / 2, (a["y0"] + a["y1b"]) / 2
    bcx, bcy = (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1b"]) / 2
    h_gap = max(b["x0"] - a["x1"], a["x0"] - b["x1"])
    v_gap = max(b["y0"] - a["y1b"], a["y0"] - b["y1b"])
    if h_gap >= v_gap:
        return ("right", "left") if bcx >= acx else ("left", "right")
    return ("bottom", "top") if bcy >= acy else ("top", "bottom")


def anchor(box, side, t=0.5):
    """Point just outside the given side at fraction t along it, plus the
    matching Excalidraw fixedPoint."""
    w, h = box["w"] or 1, box["h"] or 1
    t = 0.5001 if t == 0.5 else t
    if side == "right":
        return (box["x1"] + GAP, box["y0"] + h * t), [1 + GAP / w, t]
    if side == "left":
        return (box["x0"] - GAP, box["y0"] + h * t), [-GAP / w, t]
    if side == "top":
        return (box["x0"] + w * t, box["y0"] - GAP), [t, -GAP / h]
    bottom = box["y1b"]
    return (box["x0"] + w * t, bottom + GAP), [t, (bottom + GAP - box["y0"]) / h]


def route(s, e, s_side, e_side, via_x=None, via_y=None):
    sdx, sdy = SIDES[s_side]
    edx, edy = SIDES[e_side]
    s_h, e_h = sdx != 0, edx != 0
    (sx, sy), (ex, ey) = s, e

    if s_h and e_h:
        forward = (ex - sx) * sdx > 0 and edx == -sdx
        if via_x is not None or forward or edx == sdx:
            if via_x is None:
                if edx == sdx:
                    via_x = max(sx, ex) + STUB if sdx > 0 else min(sx, ex) - STUB
                else:
                    via_x = (sx + ex) / 2
            pts = [s, (via_x, sy), (via_x, ey), e]
        else:
            mid_y = via_y if via_y is not None else (sy + ey) / 2
            pts = [s, (sx + sdx * STUB, sy), (sx + sdx * STUB, mid_y),
                   (ex + edx * STUB, mid_y), (ex + edx * STUB, ey), e]
    elif not s_h and not e_h:
        forward = (ey - sy) * sdy > 0 and edy == -sdy
        if via_y is not None or forward or edy == sdy:
            if via_y is None:
                if edy == sdy:
                    via_y = max(sy, ey) + STUB if sdy > 0 else min(sy, ey) - STUB
                else:
                    via_y = (sy + ey) / 2
            pts = [s, (sx, via_y), (ex, via_y), e]
        else:
            mid_x = via_x if via_x is not None else (sx + ex) / 2
            pts = [s, (sx, sy + sdy * STUB), (mid_x, sy + sdy * STUB),
                   (mid_x, ey + edy * STUB), (ex, ey + edy * STUB), e]
    elif s_h:
        pts = [s, (ex, sy), e]
    else:
        pts = [s, (sx, ey), e]
    return simplify(pts)


def simplify(pts):
    out = []
    for p in pts:
        p = (round(p[0], 2), round(p[1], 2))
        if out and abs(out[-1][0] - p[0]) < 0.5 and abs(out[-1][1] - p[1]) < 0.5:
            continue
        out.append(p)
    i = 1
    while i < len(out) - 1:
        a, b, c = out[i - 1], out[i], out[i + 1]
        if (abs(a[0] - b[0]) < 0.5 and abs(b[0] - c[0]) < 0.5) or \
           (abs(a[1] - b[1]) < 0.5 and abs(b[1] - c[1]) < 0.5):
            out.pop(i)
        else:
            i += 1
    return out


def side_of(fixed_point):
    fx, fy = fixed_point
    if fx >= 1:
        return "right"
    if fx <= 0:
        return "left"
    return "top" if fy <= 0 else "bottom"


def occupied_sides(elements):
    """(element id, side) pairs already used by arrows on the canvas."""
    used = {}
    for el in elements.values():
        if el.get("type") != "arrow":
            continue
        for key in ("startBinding", "endBinding"):
            b = el.get(key) or {}
            if b.get("elementId") and b.get("fixedPoint"):
                slot = (b["elementId"], side_of(b["fixedPoint"]))
                used[slot] = used.get(slot, 0) + 1
    return used


def plan_sides(specs, elements):
    """Pick sides for every arrow, then spread arrows sharing the same
    element side along it (ordered by the far end) so they don't overlap."""
    plans = []
    for spec in specs:
        for key in ("from", "to"):
            if spec.get(key) not in elements:
                fail(f"element '{spec.get(key)}' not found on canvas", 2)
        a = bbox(elements[spec["from"]], elements)
        b = bbox(elements[spec["to"]], elements)
        s_side, e_side = auto_sides(a, b)
        plans.append({
            "a": a, "b": b,
            "s_side": spec.get("fromSide") or s_side,
            "e_side": spec.get("toSide") or e_side,
            "s_t": 0.5, "e_t": 0.5,
        })

    slots = {}
    for i, (spec, plan) in enumerate(zip(specs, plans)):
        far_b = plan["b"]
        far_a = plan["a"]
        slots.setdefault((spec["from"], plan["s_side"]), []).append((i, "s_t", far_b))
        slots.setdefault((spec["to"], plan["e_side"]), []).append((i, "e_t", far_a))
    for (_, side), users in slots.items():
        if len(users) < 2:
            continue
        horizontal_side = side in ("top", "bottom")
        users.sort(key=lambda u: (u[2]["x0"] + u[2]["x1"]) if horizontal_side else (u[2]["y0"] + u[2]["y1"]))
        for rank, (i, key, _) in enumerate(users):
            plans[i][key] = round((rank + 1) / (len(users) + 1), 4)
    return plans


def snap_straight(plan, spec):
    """For facing sides whose spans overlap, move an unshared anchor so the
    arrow is a single straight segment instead of a small jog."""
    if spec.get("viaX") is not None or spec.get("viaY") is not None:
        return
    pair = {plan["s_side"], plan["e_side"]}
    if pair == {"left", "right"}:
        lo, hi, span = "y0", "y1", "h"
    elif pair == {"top", "bottom"}:
        lo, hi, span = "x0", "x1", "w"
    else:
        return
    a, b = plan["a"], plan["b"]
    pad = 6
    if plan["e_t"] == 0.5:
        pos = a[lo] + a[span] * plan["s_t"]
        if b[lo] + pad <= pos <= b[hi] - pad:
            plan["e_t"] = round((pos - b[lo]) / (b[span] or 1), 4)
            return
    if plan["s_t"] == 0.5:
        pos = b[lo] + b[span] * plan["e_t"]
        if a[lo] + pad <= pos <= a[hi] - pad:
            plan["s_t"] = round((pos - a[lo]) / (a[span] or 1), 4)


def build_arrow(spec, plan, elements):
    a_el, b_el = elements[spec["from"]], elements[spec["to"]]
    s_side, e_side = plan["s_side"], plan["e_side"]
    snap_straight(plan, spec)
    (s, s_fp) = anchor(plan["a"], s_side, plan["s_t"])
    (e, e_fp) = anchor(plan["b"], e_side, plan["e_t"])
    pts = route(s, e, s_side, e_side, spec.get("viaX"), spec.get("viaY"))

    arrow_id = spec.get("id") or f"arrow-{spec['from']}-{spec['to']}-{secrets.token_hex(2)}"
    ox, oy = pts[0]
    arrow = {
        "id": arrow_id,
        "type": "arrow",
        "x": ox,
        "y": oy,
        "width": max(p[0] for p in pts) - min(p[0] for p in pts),
        "height": max(p[1] for p in pts) - min(p[1] for p in pts),
        "points": [[round(px - ox, 2), round(py - oy, 2)] for px, py in pts],
        "elbowed": True,
        "roughness": 0,
        "strokeColor": spec.get("color", "#1e1e1e"),
        "strokeWidth": spec.get("strokeWidth", 2),
        "strokeStyle": "dashed" if spec.get("dashed") else "solid",
        "endArrowhead": "arrow",
        "startBinding": {"elementId": a_el["id"], "focus": 0, "gap": GAP, "fixedPoint": s_fp},
        "endBinding": {"elementId": b_el["id"], "focus": 0, "gap": GAP, "fixedPoint": e_fp},
    }
    label = None
    if spec.get("label"):
        # A real bound text element (not the `label` shorthand) so the font
        # applies without waiting for a browser round-trip.
        text = spec["label"]
        font_size = spec.get("fontSize", 16)
        seg = max(zip(pts, pts[1:]), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
        mx, my = (seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2
        tw, th = len(text) * font_size * 0.6, font_size * 1.25
        label = {
            "id": f"{arrow_id}-label",
            "type": "text",
            "x": round(mx - tw / 2, 2),
            "y": round(my - th / 2, 2),
            "width": round(tw, 2),
            "height": round(th, 2),
            "text": text,
            "originalText": text,
            "fontSize": font_size,
            "fontFamily": spec.get("fontFamily", "cascadia"),
            "textAlign": "center",
            "verticalAlign": "middle",
            "containerId": arrow_id,
            "strokeColor": arrow["strokeColor"],
        }
        arrow["boundElements"] = [{"id": label["id"], "type": "text"}]
    return arrow, label


def cmd(args):
    if args.from_id == "-":
        specs = json.load(sys.stdin)
        if not isinstance(specs, list):
            fail("stdin must be a JSON array of arrow specs", 2)
    else:
        if not args.to_id:
            fail("usage: excalidraw-connect <from-id> <to-id> [options] (or '-' for stdin)", 2)
        specs = [{
            "from": args.from_id, "to": args.to_id, "label": args.label,
            "color": args.color, "dashed": args.dashed, "id": args.id,
            "fromSide": args.from_side, "toSide": args.to_side,
            "viaX": args.via_x, "viaY": args.via_y,
        }]
        specs = [{k: v for k, v in specs[0].items() if v not in (None, False)}]

    base = args.url.rstrip("/")
    elements = {el["id"]: el for el in http(f"{base}/api/elements").get("elements", [])}
    plans = plan_sides(specs, elements)
    used = occupied_sides(elements)
    warnings = []
    for spec, plan in zip(specs, plans):
        for el_id, side, flag in ((spec["from"], plan["s_side"], "--from-side"),
                                  (spec["to"], plan["e_side"], "--to-side")):
            if used.get((el_id, side)):
                warnings.append(f"{el_id}:{side} already has {used[(el_id, side)]} arrow(s); "
                                f"arrows may overlap — use {flag} with a free side, or draw them in one batch")
    built = [build_arrow(spec, plan, elements) for spec, plan in zip(specs, plans)]
    arrows = [a for a, _ in built]
    labels = [lbl for _, lbl in built if lbl]

    resp = http(f"{base}/api/elements/batch", {"elements": arrows + labels}, "POST")
    if not resp.get("success"):
        fail(f"canvas rejected arrows: {resp.get('error')}")

    # Register arrows on their endpoint shapes so they stay attached in the UI.
    bound = {}
    for arr in arrows:
        for key in ("startBinding", "endBinding"):
            bound.setdefault(arr[key]["elementId"], []).append(arr["id"])
    for el_id, arrow_ids in bound.items():
        existing = elements[el_id].get("boundElements") or []
        have = {b["id"] for b in existing}
        merged = existing + [{"id": i, "type": "arrow"} for i in arrow_ids if i not in have]
        http(f"{base}/api/elements/{el_id}", {"boundElements": merged}, "PUT")

    out = {"success": True, "arrows": [
        {"id": a["id"], "from": a["startBinding"]["elementId"], "to": a["endBinding"]["elementId"],
         "points": len(a["points"]), "labelId": lbl["id"] if lbl else None}
        for a, lbl in built
    ]}
    if warnings:
        out["warnings"] = warnings
    print(json.dumps(out, indent=2))


def main():
    p = argparse.ArgumentParser(
        prog="excalidraw-connect",
        description="Draw orthogonal (elbow) arrows between canvas elements, bound to both ends.",
        epilog="Sides are picked automatically (horizontal gap -> right/left, else bottom/top). "
               "Use --via-x/--via-y to route the middle segment through a gutter between zones.",
    )
    p.add_argument("--url", default=os.environ.get("EXPRESS_SERVER_URL", "http://127.0.0.1:3000"),
                   help="canvas URL (default: $EXPRESS_SERVER_URL)")
    p.add_argument("from_id", help="source element id, or '-' to read a JSON array of specs from stdin")
    p.add_argument("to_id", nargs="?", help="target element id")
    p.add_argument("--label", help="arrow label, e.g. '(1) send logs'")
    p.add_argument("--color", help="stroke color (label inherits it), e.g. '#1971c2'")
    p.add_argument("--dashed", action="store_true", help="dashed line (secondary flows only)")
    p.add_argument("--id", help="arrow id")
    p.add_argument("--from-side", choices=SIDES, help="force exit side on the source")
    p.add_argument("--to-side", choices=SIDES, help="force entry side on the target")
    p.add_argument("--via-x", type=float, help="x of the vertical middle segment")
    p.add_argument("--via-y", type=float, help="y of the horizontal middle segment")
    args = p.parse_args()
    try:
        cmd(args)
    except RuntimeError as e:
        fail(str(e), 3)


if __name__ == "__main__":
    main()
