"""Kennzahlen, Urteil, Stufen des Steppers und die Experimente der Demo (Gebrochenheit, Reihenfolge, Preis des Teilens, Entkopplung, Größe).
Rechnet mit ganzen Zahlen und HiGHS; Vergleiche mit Toleranz."""

import itertools
from dataclasses import dataclass
from functools import lru_cache
from statistics import mean, median

import numpy as np

import mcf_constants as C
import mcf_model as md
import mcf_solve as sv

TOL = 1e-6


def pct(numerator, denominator, digits=1):
    return round(100 * numerator / denominator, digits) if denominator else 0.0


def build(net, K, p, d, s, density, spread, load, seed):
    """Modell zu den Einstellungen; feste Netze ignorieren die Zufallsparameter."""
    if net == "gap":
        return md.gap_net()
    if net == "order":
        return md.order_net()
    return md.generate_mcf(p, d, s, density, spread, load, seed, K)


def heuristic_orders(mcf):
    """Reihenfolgen: wie angegeben, billigstes Gut (kleinster Kostenfaktor bzw. kleinste Einzelkosten) zuerst, größte Nachfrage zuerst."""
    given = tuple(range(mcf.K))
    cost_key = [sum(mcf.cost(k, e) for e in range(mcf.m) if not mcf.reward[e]) for k in range(mcf.K)]
    cheap = tuple(sorted(range(mcf.K), key=lambda k: (mcf.factors[k], cost_key[k], k)))
    large = tuple(sorted(range(mcf.K), key=lambda k: (-mcf.demand(k), k)))
    return {"given": given, "cheap": cheap, "large": large}


def all_orders(mcf, lp_objective):
    """Alle K! Reihenfolgen mit ihrer sequentiellen Lösung: (beste, schlechteste, Liste)."""
    sols = {o: sv.solve_sequential(mcf, o) for o in itertools.permutations(range(mcf.K))}
    best = min(sols, key=lambda o: (sols[o].objective, o))
    worst = max(sols, key=lambda o: (sols[o].objective, o))
    return best, worst, sols


@dataclass(frozen=True)
class Stage:
    kind: str            # 'single' | 'seq' | 'lp' | 'ilp' | 'decoupled'
    title: str
    x: np.ndarray        # (K, m)
    delivered: tuple
    cost: float
    note: str
    over: dict           # Überlastung je Kante (nur single / decoupled)
    step: int = -1       # bei 'seq': Nummer des Guts in der Reihenfolge


@dataclass(frozen=True)
class Analysis:
    mcf: md.Mcf
    lp: sv.Solution
    ilp: sv.Solution
    single: sv.Solution
    over: dict
    seq: sv.Solution
    order: tuple
    order_key: str
    best: tuple
    worst: tuple
    seq_by_order: dict
    lagrange: float
    decoupled_x: np.ndarray
    decoupled_over: dict
    stages: tuple


def _decoupled_solution(mcf, flows):
    x = np.array(flows, dtype=float)
    delivered = tuple(float(sum(x[k, e] for e in range(mcf.m) if mcf.reward[e])) for k in range(mcf.K))
    cost = float(sum(mcf.cost(k, e) * x[k, e] for k in range(mcf.K) for e in range(mcf.m) if not mcf.reward[e]))
    caps = [a[2] for a in mcf.net.arcs]
    over = {e: float(x[:, e].sum() - caps[e]) for e in range(mcf.m) if mcf.joint[e] and x[:, e].sum() > caps[e] + TOL}
    return x, delivered, cost, over


def analyse(mcf, order_key=C.DEFAULT_ORDER):
    lp = sv.solve_lp(mcf)
    ilp = sv.solve_ilp(mcf)
    single, over = sv.solve_single(mcf)
    heur = heuristic_orders(mcf)
    best, worst, seq_by_order = all_orders(mcf, lp.objective)
    order = {**heur, "best": best, "worst": worst}[order_key]
    seq = seq_by_order[order]
    lagrange, dflows = sv.decouple(mcf, lp.duals)
    dx, ddel, dcost, dover = _decoupled_solution(mcf, dflows)
    stages = [Stage("single", "Jedes Gut allein", single.x, single.delivered, single.cost, "Jedes Gut bekommt den billigsten Fluss auf der vollen Kapazität - ohne Rücksicht auf die anderen.", over)]
    left_x = np.zeros_like(single.x)
    left_del = [0.0] * mcf.K
    cum = np.zeros_like(single.x)
    for i, k in enumerate(order):
        partial = sv.solve_sequential(mcf, order[:i + 1]) if False else None
        cum = np.where(np.arange(mcf.K)[:, None] == k, seq.x, cum)
        delivered = tuple(float(sum(cum[j, e] for e in range(mcf.m) if mcf.reward[e])) for j in range(mcf.K))
        cost = float(sum(mcf.cost(j, e) * cum[j, e] for j in range(mcf.K) for e in range(mcf.m) if not mcf.reward[e]))
        stages.append(Stage("seq", f"Nacheinander: {mcf.names[k]}", cum.copy(), delivered, cost, f"{mcf.names[k]} fährt auf der Restkapazität der vorigen Güter.", {}, i))
    stages.append(Stage("lp", "Gemeinsames LP", lp.x, lp.delivered, lp.cost, "Alle Güter gemeinsam, optimal; an den bindenden Kanten stehen die Schattenpreise.", {}))
    stages.append(Stage("ilp", "Ganzzahlig", ilp.x, ilp.delivered, ilp.cost, "Jede Flusseinheit unteilbar.", {}))
    stages.append(Stage("decoupled", "Preise entkoppeln die Güter", dx, ddel, dcost, "Mit den Schattenpreisen ist jedes Gut ein gewöhnlicher Min-Cost-Flow.", dover))
    return Analysis(mcf, lp, ilp, single, over, seq, order, order_key, best, worst, seq_by_order, lagrange, dx, dover, tuple(stages))


def verdict(a):
    """(Stufe, Code, Daten): 'integral' = das LP ist ganzzahlig, 'fractional' = das LP ist gebrochen (ganzzahlig geht weniger), 'nothing' = nichts lieferbar."""
    mcf, lp, ilp = a.mcf, a.lp, a.ilp
    demand = mcf.total_demand()
    binding = [e for e in range(mcf.m) if a.lp.duals[e] > TOL]
    data = {
        "K": mcf.K, "demand": demand, "lp_delivered": lp.total_delivered, "lp_cost": lp.cost, "ilp_delivered": ilp.total_delivered, "ilp_cost": ilp.cost,
        "deliv_gap": lp.total_delivered - ilp.total_delivered, "cost_gap": ilp.cost - lp.cost, "fractional": lp.fractional, "n_fractional": lp.n_fractional, "max_fraction": lp.max_fraction,
        "seq_delivered": a.seq.total_delivered, "seq_cost": a.seq.cost, "seq_loss": lp.total_delivered - a.seq.total_delivered, "single_delivered": a.single.total_delivered,
        "n_over": len(a.over), "over_total": sum(a.over.values()), "binding": binding, "n_binding": len(binding), "price_sum": float(a.lp.duals.sum()), "iterations": lp.iterations,
        "n_vars": lp.n_vars, "n_eq": lp.n_eq, "n_ub": lp.n_ub, "lagrange": a.lagrange, "lagrange_err": abs(a.lagrange - lp.objective), "dec_over": len(a.decoupled_over),
        "order": a.order, "best_loss": lp.total_delivered - a.seq_by_order[a.best].total_delivered, "worst_loss": lp.total_delivered - a.seq_by_order[a.worst].total_delivered,
        "share": pct(lp.total_delivered, demand) if demand else None, "delivered": lp.delivered, "goods_demand": [mcf.demand(k) for k in range(mcf.K)],
    }
    if lp.total_delivered < TOL:
        return "warning", "nothing", data
    if lp.fractional:
        return "warning", "fractional", data
    return "success", "integral", data


# --- Verteilungen über feste Netze ---------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=64)
def _model(net_key, K, p, d, s, density, spread, load, seed):
    return build(net_key, K, p, d, s, density, spread, load, seed)


@lru_cache(maxsize=64)
def _runs(K, p, d, s, density, spread, load, seeds=C.DIST_SEEDS, orders=True):
    """Je Netz LP, ILP, Einzellösung, Reihenfolge-Heuristiken (und bei K <= 4 alle Reihenfolgen) und die Entkopplung; von den Verteilungen gemeinsam genutzt."""
    out = []
    for seed in seeds:
        mcf = md.generate_mcf(p, d, s, density, spread, load, seed, K)
        lp = sv.solve_lp(mcf)
        ilp = sv.solve_ilp(mcf)
        single, over = sv.solve_single(mcf)
        heur = heuristic_orders(mcf)
        seqs = {name: sv.solve_sequential(mcf, o) for name, o in heur.items()}
        row = {"mcf": mcf, "lp": lp, "ilp": ilp, "single": single, "over": over, "seqs": seqs}
        if orders and K <= 4:
            best, worst, allsols = all_orders(mcf, lp.objective)
            row["best"], row["worst"], row["all"] = allsols[best], allsols[worst], allsols
        lagrange, dflows = sv.decouple(mcf, lp.duals)
        dx, _, _, dover = _decoupled_solution(mcf, dflows)
        row["lagrange_err"] = abs(lagrange - lp.objective)
        row["dec_over"] = len(dover)
        row["dec_x"] = dx
        out.append(row)
    return out


@lru_cache(maxsize=64)
def distribution(K, p, d, s, density, spread, load, seeds=C.DIST_SEEDS):
    """Über feste Netze: Gebrochenheit, Kosten der Ganzzahligkeit, Preis des Teilens, Reihenfolge-Heuristiken, Entkopplung, Größe."""
    runs = _runs(K, p, d, s, density, spread, load, seeds)
    n = len(runs)
    cols = {k: [] for k in ("lp_delivered", "demand", "lp_cost", "over", "binding", "iterations", "n_vars", "single_overshoot", "price_sum", "deliv_gap")}
    seq_loss = {name: [] for name in ("given", "cheap", "large")}
    seq_opt = {name: 0 for name in ("given", "cheap", "large")}
    fractional = ilp_worse = dec_over = 0
    best_opt = worst_bad = 0
    best_loss, worst_loss = [], []
    lag_err = 0.0
    for r in runs:
        lp, ilp, mcf = r["lp"], r["ilp"], r["mcf"]
        cols["lp_delivered"].append(lp.total_delivered)
        cols["demand"].append(mcf.total_demand())
        cols["lp_cost"].append(lp.cost)
        cols["over"].append(len(r["over"]))
        cols["binding"].append(int(sum(1 for e in range(mcf.m) if lp.duals[e] > TOL)))
        cols["iterations"].append(lp.iterations)
        cols["n_vars"].append(lp.n_vars)
        cols["single_overshoot"].append(r["single"].total_delivered - lp.total_delivered)
        cols["price_sum"].append(float(lp.duals.sum()))
        cols["deliv_gap"].append(lp.total_delivered - ilp.total_delivered)
        fractional += lp.fractional
        ilp_worse += ilp.objective > lp.objective + TOL
        dec_over += r["dec_over"] > 0
        lag_err = max(lag_err, r["lagrange_err"])
        for name, sol in r["seqs"].items():
            loss = lp.total_delivered - sol.total_delivered
            seq_loss[name].append(loss)
            seq_opt[name] += sol.objective <= lp.objective + TOL
        if "best" in r:
            best_loss.append(lp.total_delivered - r["best"].total_delivered)
            worst_loss.append(lp.total_delivered - r["worst"].total_delivered)
            best_opt += r["best"].objective <= lp.objective + TOL
            worst_bad += r["worst"].objective > lp.objective + TOL
    out = {"n_seeds": n, "cols": cols, "share_fractional": fractional / n, "share_ilp_worse": ilp_worse / n, "share_dec_over": dec_over / n, "lagrange_err_max": lag_err,
           "seq_loss": seq_loss, "share_seq_optimal": {k: v / n for k, v in seq_opt.items()}, "nodes_mean": mean(r["mcf"].net.n for r in runs), "edges_mean": mean(r["mcf"].m for r in runs)}
    if best_loss:
        out.update({"best_loss": best_loss, "worst_loss": worst_loss, "share_best_optimal": best_opt / n, "share_worst_bad": worst_bad / n})
    for k, v in cols.items():
        out[k + "_mean"], out[k + "_median"], out[k + "_max"] = mean(v), median(v), max(v)
    return out


@lru_cache(maxsize=16)
def pair_table(families=C.PAIR_FAMILIES, seeds=C.DIST_SEEDS):
    """Frachtnetze mit Quelle-Ziel-Paaren (Kapazität und Menge 1): Anteil gebrochener LPs und Lücke der Ganzzahligkeit je Familie (Knoten, Dichte, Güter)."""
    rows = []
    for (n, dens, K) in families:
        frac = worse = 0
        gap = []
        for seed in seeds:
            mcf = md.generate_pairs(n, dens, K, seed, 1, 1)
            lp = sv.solve_lp(mcf)
            if lp.fractional:
                frac += 1
                ilp = sv.solve_ilp(mcf)
                worse += ilp.objective > lp.objective + TOL
                gap.append(lp.total_delivered - ilp.total_delivered)
        rows.append({"family": (n, dens, K), "fractional": frac, "ilp_worse": worse, "gap_max": max(gap) if gap else 0.0, "n": len(seeds)})
    return rows


@lru_cache(maxsize=16)
def size_table(sizes=C.SCALE_SIZES, ks=C.K_SWEEP, seeds=C.SCALE_SEEDS):
    """Größe des LP: Variablen K·m, Nebenbedingungen und HiGHS-Iterationen je Netzgröße und Zahl der Güter (Mittel über die Netze)."""
    rows = []
    for (p, d, s) in sizes:
        for K in ks:
            cols = {"vars": [], "eq": [], "ub": [], "nit": [], "m": []}
            for seed in seeds:
                mcf = md.generate_mcf(p, d, s, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, seed, K)
                lp = sv.solve_lp(mcf)
                cols["vars"].append(lp.n_vars); cols["eq"].append(lp.n_eq); cols["ub"].append(lp.n_ub); cols["nit"].append(lp.iterations); cols["m"].append(mcf.m)
            rows.append({"size": (p, d, s), "K": K, **{k: mean(v) for k, v in cols.items()}})
    return rows


def slopes(rows):
    x = np.log([r["vars"] for r in rows])
    return {k: float(np.polyfit(x, np.log([max(r[k], 1) for r in rows]), 1)[0]) for k in ("eq", "nit")}
