"""Plotly-Abbildungen: Netz mit den Flüssen der Güter (parallel gezeichnet), Stufen (Lieferung und Kosten), Lieferverlust der Reihenfolge-Heuristiken, Größe des LP.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Kanten haben über unsichtbare Marker einen Hover-Text
(Plotly-Linien reagieren nur an ihren Stützpunkten)."""

from math import atan2, degrees, hypot

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import mcf_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _layout(fig, net, height):
    xs = [p[0] for p in net.pos]
    ys = [p[1] for p in net.pos]
    pad = 9
    fig.update_xaxes(visible=False, range=[min(xs) - pad, max(xs) + pad], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[min(ys) - pad, max(ys) + pad])
    return _base(fig, height)


def _curve(p0, p1, bulge, steps=8):
    """Punkte von p0 nach p1; mit `bulge` > 0 als flacher Bogen nach rechts (so trennen sich Vorwärts- und Rückkante). Dazu der Pfeilwinkel bei 65 %."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = hypot(dx, dy) or 1.0
    cx, cy = (x0 + x1) / 2 + bulge * length * dy / length, (y0 + y1) / 2 - bulge * length * dx / length
    ts = [k / steps for k in range(steps + 1)]
    xs = [(1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1 for t in ts]
    ys = [(1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1 for t in ts]
    t = 0.65
    tx = 2 * (1 - t) * (cx - x0) + 2 * t * (x1 - cx)
    ty = 2 * (1 - t) * (cy - y0) + 2 * t * (y1 - cy)
    ax = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
    ay = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
    return xs, ys, (ax, ay, degrees(atan2(tx, ty))), (xs[steps // 2], ys[steps // 2])


def _segments(curves):
    x, y = [], []
    for xs, ys, _, _ in curves:
        x += xs + [None]
        y += ys + [None]
    return x, y


def _lines(fig, curves, color, width, name, dash=None, showlegend=True):
    if not curves:
        return
    x, y = _segments(curves)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=width, dash=dash), hoverinfo="skip", name=name, showlegend=showlegend))


def _arrows(fig, curves, color, size=9):
    if not curves:
        return
    fig.add_trace(go.Scatter(x=[c[2][0] for c in curves], y=[c[2][1] for c in curves], mode="markers", hoverinfo="skip", showlegend=False,
                             marker=dict(symbol="arrow", size=size, color=color, angle=[c[2][2] for c in curves])))


def _hover_points(fig, net, entries):
    """Unsichtbare Marker entlang jeder Kante, damit der Hover-Text überall auf der Kante erscheint. entries: [(Kurve, Text)]"""
    x, y, text = [], [], []
    for curve, label in entries:
        xs, ys = curve[0], curve[1]
        for k in range(1, len(xs) - 1):
            x.append(xs[k]); y.append(ys[k]); text.append(label)
    if x:
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker=dict(size=9, opacity=0), hovertext=text, hoverinfo="text", showlegend=False))


def _labels(fig, points):
    """points: [(x, y, Text)] - als Annotationen mit heller Hinterlegung, damit sie Kanten, Pfeile und Knotenbeschriftungen nicht unlesbar machen."""
    for x, y, text in points:
        fig.add_annotation(x=x, y=y, text=text, showarrow=False, xanchor="left", font=dict(size=11, color="#111"), bgcolor="rgba(255,255,255,0.88)", borderpad=1)


def _arc_name(net, i):
    u, v = net.arcs[i][0], net.arcs[i][1]
    return f"{net.names[u]} → {net.names[v]}"


def _nodes(fig, net, reach=None):
    """Knoten: S und T als Quadrate, alle anderen als Kreise; mit `reach` grün (von S erreichbar) oder grau eingefärbt."""
    text_pos = {0: "top center", 1: "bottom center"}
    for kind, idx in (("Quelle/Senke", [net.s, net.t]), ("Knoten", [v for v in range(net.n) if v not in (net.s, net.t)])):
        colors = [C.COLORS["node"] if reach is None else (C.COLORS["reach"] if reach[v] else C.COLORS["unreach"]) for v in idx]
        pos = [text_pos.get(v, "top center" if net.pos[v][1] > 70 else ("bottom center" if net.pos[v][1] < 30 else "middle left")) for v in idx]
        if net.logistic and kind == "Knoten":
            pos = ["top center" if net.names[v].startswith("Werk") else "bottom center" if net.names[v].startswith("Filiale") else "middle left" for v in idx]
        fig.add_trace(go.Scatter(
            x=[net.pos[v][0] for v in idx], y=[net.pos[v][1] for v in idx], mode="markers+text", showlegend=False,
            text=[net.labels[v] for v in idx], textposition=pos, hovertext=[net.names[v] for v in idx], hoverinfo="text",
            marker=dict(symbol="square" if kind == "Quelle/Senke" else "circle", size=13 if kind == "Quelle/Senke" else 10, color=colors, line=dict(width=1.5, color="#333"))))


def _wscale(net):
    return max(c for _, _, c, _, _ in net.arcs)


def _width(amount, top, lo=1.0, hi=6.0):
    return lo + (hi - lo) * amount / top if top else lo


def _node_text_positions(net, idx):
    if net.logistic:
        return ["top center" if (v == 0 or net.names[v].startswith("Werk")) else "bottom center" if (v == 1 or net.names[v].startswith("Filiale")) else "middle left" for v in idx]
    return ["top center" if v == net.s else "bottom center" if v == net.t else "middle left" for v in idx]


TOL = 1e-6


def _shift(curve, dx, dy):
    xs, ys, (ax, ay, ang), (mx, my) = curve
    return [x + dx for x in xs], [y + dy for y in ys], (ax + dx, ay + dy, ang), (mx + dx, my + dy)


def _fmt(x):
    return f"{x:.1f}".replace(".", ",") if abs(x - round(x)) > TOL else f"{round(x)}"


def build_mcf(mcf, stage, duals=None, height=460):
    """Netz mit den Flüssen der Güter: je Gut eine Farbe, parallel nebeneinander gezeichnet (Breite ~ Fluss, gestrichelt = gebrochener Fluss). Rote Unterlage = die Summe der Güter überschreitet
    die gemeinsame Kapazität; orange Unterlage = bindende Kapazität mit Schattenpreis (`duals`). Beschriftet werden nur die auffälligen Kanten (Überlast, Schattenpreis, gebrochener Fluss) und bei kleinen Netzen jede Kante mit Fluss."""
    net = mcf.net
    fig = go.Figure()
    x = stage.x
    K = mcf.K
    caps = [a[2] for a in net.arcs]
    top = max((caps[e] for e in range(mcf.m) if mcf.joint[e]), default=1)
    bulge = 0.0 if net.logistic else 0.12
    groups, faint, under_over, under_bind, hover, labels = {}, [], [], [], [], []
    small = mcf.m <= 30
    for e, (u, v, cap, cost, kind) in enumerate(net.arcs):
        base = _curve(net.pos[u], net.pos[v], bulge)
        load = float(x[:, e].sum())
        parts = ", ".join(f"{mcf.names[k]} {_fmt(x[k, e])}" for k in range(K) if x[k, e] > TOL)
        hover.append((base, f"{_arc_name(net, e)}: Summe {_fmt(load)}" + (f" von {cap}" if mcf.joint[e] else "") + (f" ({parts})" if parts else "")))
        faint.append(base)
        over = e in stage.over
        bind = duals is not None and mcf.joint[e] and duals[e] > TOL
        if over:
            under_over.append(base)
        if bind:
            under_bind.append(base)
        dx0, dy0 = net.pos[v][0] - net.pos[u][0], net.pos[v][1] - net.pos[u][1]
        length = (dx0 ** 2 + dy0 ** 2) ** 0.5 or 1.0
        nx, ny = -dy0 / length, dx0 / length
        active = [k for k in range(K) if x[k, e] > TOL]
        for j, k in enumerate(active):
            off = (j - (len(active) - 1) / 2) * 1.1
            f = x[k, e]
            frac = abs(f - round(f)) > TOL
            groups.setdefault((k, max(1, round(1.5 + 5 * f / top)), frac), []).append(_shift(base, nx * off, ny * off))
        if over:
            labels.append((base[0][3] + 1.5, base[1][3], f"{_fmt(load)} > {cap}"))
        elif bind:
            labels.append((base[0][3] + 1.5, base[1][3], f"λ {duals[e]:.0f}"))
        elif any(abs(x[k, e] - round(x[k, e])) > TOL for k in range(K)):
            labels.append((base[0][3] + 1.5, base[1][3], "/".join(_fmt(x[k, e]) for k in active)))
        elif small and load > TOL:
            labels.append((base[0][3] + 1.5, base[1][3], f"{_fmt(load)}" + (f"/{cap}" if mcf.joint[e] else "")))
    _lines(fig, under_over, "rgba(214,39,40,0.35)", 12, "überlastet: Summe > Kapazität")
    _lines(fig, under_bind, "rgba(255,127,14,0.35)", 12, "bindend: Schattenpreis λ")
    _lines(fig, faint, C.COLORS["faint"], 1.0, "Kante", showlegend=False)
    for (k, w, frac), curves in sorted(groups.items()):
        _lines(fig, curves, mcf_color(k), w, mcf.names[k], dash="dot" if frac else None, showlegend=False)
    for k in range(K):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=mcf_color(k), width=4), name=mcf.names[k]))
    if any(f for (_, _, f) in groups):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#555", width=3, dash="dot"), name="gestrichelt: gebrochener Fluss"))
    if net.m <= 80:
        _arrows(fig, faint, "rgba(60,60,60,0.55)", 7)
    _hover_points(fig, net, hover)
    _labels(fig, labels)
    idx = list(range(net.n))
    fig.add_trace(go.Scatter(x=[net.pos[v][0] for v in idx], y=[net.pos[v][1] for v in idx], mode="markers+text", showlegend=False, text=[net.labels[v] for v in idx], textposition=_node_text_positions(net, idx),
                             hovertext=[net.names[v] for v in idx], hoverinfo="text", marker=dict(symbol=["square" if v in (net.s, net.t) else "circle" for v in idx], size=[13 if v in (net.s, net.t) else 10 for v in idx],
                                                                                              color=C.COLORS["node"], line=dict(width=1.5, color="#333"))))
    fig = _layout(fig, net, height)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=70), legend=dict(orientation="h", y=-0.12))
    return fig


def mcf_color(k):
    import mcf_model as md
    return md.GOOD_COLORS[k % len(md.GOOD_COLORS)]


def build_stages(stages, current, names, demand, height=330):
    """Lieferung je Stufe (oben, gestapelt nach Gütern, gestrichelt die Nachfrage) und echte Kosten (unten); die gezeigte Stufe voll, die übrigen blass."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.14, row_heights=[0.58, 0.42])
    labels = [f"{i}" for i in range(len(stages))]
    short = {"single": "allein", "lp": "LP", "ilp": "ganz-\nzahlig", "decoupled": "Preise"}
    xs = [short.get(s.kind, f"{s.step + 1}. Gut") for s in stages]
    for k, name in enumerate(names):
        fig.add_trace(go.Bar(x=list(range(len(stages))), y=[s.delivered[k] for s in stages], name=name, marker_color=mcf_color(k), opacity=1.0,
                             marker=dict(color=mcf_color(k), opacity=[1.0 if i == current else 0.35 for i in range(len(stages))]),
                             hovertext=[f"{s.title}: {name} {_fmt(s.delivered[k])}" for s in stages], hoverinfo="text"), row=1, col=1)
    fig.update_layout(barmode="stack")
    fig.add_trace(go.Scatter(x=[-0.5, len(stages) - 0.5], y=[demand, demand], mode="lines", line=dict(color="#555", dash="dash"), name=f"Nachfrage {demand}", hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Bar(x=list(range(len(stages))), y=[s.cost for s in stages], marker=dict(color=C.COLORS["flow"], opacity=[0.9 if i == current else 0.3 for i in range(len(stages))]), showlegend=False,
                         hovertext=[f"{s.title}: Kosten {_fmt(s.cost)}" for s in stages], hoverinfo="text"), row=2, col=1)
    fig.update_yaxes(title="geliefert", row=1, col=1, rangemode="tozero")
    fig.update_yaxes(title="Kosten", row=2, col=1, rangemode="tozero")
    fig.update_xaxes(tickmode="array", tickvals=list(range(len(stages))), ticktext=xs, row=2, col=1)
    fig = _base(fig, height + 40)
    fig.update_layout(legend=dict(orientation="h", y=-0.3), margin=dict(l=10, r=10, t=10, b=60))
    return fig


def build_loss_hist(losses, current=None, height=300):
    """Lieferverlust der Reihenfolge-Heuristiken gegen das LP (in Einheiten), je Netz, übereinandergelegt."""
    fig = go.Figure()
    for name, values, color in (("wie angegeben", losses.get("given"), "#1f77b4"), ("billigstes zuerst", losses.get("cheap"), "#2ca02c"), ("größte Nachfrage zuerst", losses.get("large"), "#ff7f0e")):
        if values is not None:
            fig.add_trace(go.Histogram(x=values, xbins=dict(size=1), name=name, marker_color=color, opacity=0.6))
    fig.update_layout(barmode="overlay")
    if current is not None:
        fig.add_vline(x=current, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Ihre Ziehung", annotation_position="top")
    fig.update_xaxes(title="fehlende Lieferung gegen das LP [Einheiten]")
    fig.update_yaxes(title="Netze")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.35), height=height + 50, margin=dict(l=10, r=10, t=30 if current is not None else 10, b=10))
    return fig


def build_size(rows, height=340):
    """Iterationen des LP gegen die Zahl der Variablen K·m (doppelt logarithmisch), je Netzgröße eine Linie über K = 2 bis 5."""
    fig = go.Figure()
    sizes = []
    for r in rows:
        if r["size"] not in sizes:
            sizes.append(r["size"])
    for i, size in enumerate(sizes):
        sub = [r for r in rows if r["size"] == size]
        fig.add_trace(go.Scatter(x=[r["vars"] for r in sub], y=[r["nit"] for r in sub], mode="lines+markers", name=f"{size[0]}/{size[1]}/{size[2]}", text=[f"K = {r['K']}" for r in sub], hoverinfo="text+x+y"))
    fig.update_xaxes(title="Variablen K·m", type="log")
    fig.update_yaxes(title="HiGHS-Iterationen", type="log")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.3, title=dict(text="Werke/DCs/Filialen")), height=height + 50)
    return fig
