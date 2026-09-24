"""Szenario (Aufbau, Reproduzierbarkeit), Auswertung (Stufen, Urteil, Reihenfolgen, Verteilungen, Gebrochenheit, Größe)."""

import itertools

import numpy as np
import pytest

import mcf_constants as C
import mcf_evaluation as ev
import mcf_model as md
import mcf_scenario as sc
import mcf_solve as sv

DEFAULT = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


def _mcf(K=3, seed=C.DEFAULT_SEED, *settings):
    return md.generate_mcf(*(settings or DEFAULT), seed, K)


def test_structure_of_a_distribution_net():
    p, d, s = 3, 3, 8
    net = sc.generate(p, d, s, 60, 50, 90, C.DEFAULT_SEED)
    assert net.n == 2 + p + 2 * d + s and net.s == 0 and net.t == 1 and net.logistic
    kinds = [a[4] for a in net.arcs]
    assert kinds.count(sc.K_SUPPLY) == p and kinds.count(sc.K_THROUGHPUT) == d and kinds.count(sc.K_DEMAND) == s


@pytest.mark.parametrize("seed", range(10))
def test_every_good_can_reach_a_store_in_principle(seed):
    """Jedes Gut hat mindestens ein Werk und (bis auf zufällige Nullen) eine Nachfrage; das Netz selbst ist das der Vorgänger-Demos."""
    mcf = _mcf(4, seed)
    supply = [e for e, a in enumerate(mcf.net.arcs) if a[4] == sc.K_SUPPLY]
    assert all(any(mcf.ub[k][e] > 0 for e in supply) for k in range(4)) and mcf.total_demand() > 0


def test_build_dispatches_on_the_net_and_ignores_the_random_settings_for_fixed_nets():
    assert ev.build("gap", 5, 6, 6, 12, 100, 100, 160, 1) == md.gap_net() and ev.build("order", 5, 6, 6, 12, 100, 100, 160, 1) == md.order_net()
    assert ev.build("random", 3, *DEFAULT, 9) == _mcf(3, 9)


def test_heuristic_orders_are_permutations_and_follow_their_rule():
    for K in (2, 3, 5):
        mcf = _mcf(K)
        orders = ev.heuristic_orders(mcf)
        assert all(sorted(o) == list(range(K)) for o in orders.values()) and orders["given"] == tuple(range(K))
        assert [mcf.factors[k] for k in orders["cheap"]] == sorted(mcf.factors)
        assert [mcf.demand(k) for k in orders["large"]] == sorted((mcf.demand(k) for k in range(K)), reverse=True)


def test_all_orders_finds_the_best_and_the_worst():
    mcf = _mcf(3)
    lp = sv.solve_lp(mcf)
    best, worst, sols = ev.all_orders(mcf, lp.objective)
    assert len(sols) == 6 and sols[best].objective == min(s.objective for s in sols.values()) and sols[worst].objective == max(s.objective for s in sols.values())


def test_stages_have_the_documented_sequence_and_content():
    a = ev.analyse(_mcf(3))
    kinds = [s.kind for s in a.stages]
    assert kinds == ["single", "seq", "seq", "seq", "lp", "ilp", "decoupled"] and [s.step for s in a.stages if s.kind == "seq"] == [0, 1, 2]
    seq_stages = [s for s in a.stages if s.kind == "seq"]
    assert all(np.count_nonzero(np.abs(seq_stages[i].x).sum(axis=1)) <= i + 1 for i in range(3))                # nach i+1 Gütern sind höchstens i+1 Güter unterwegs
    assert np.allclose(seq_stages[-1].x, a.seq.x) and abs(seq_stages[-1].cost - a.seq.cost) < 1e-9
    assert np.allclose(a.stages[0].x, a.single.x) and np.allclose(a.stages[-3].x, a.lp.x) and np.allclose(a.stages[-2].x, a.ilp.x)
    assert len(a.stages[0].over) == len(a.over) and abs(sum(a.stages[-3].delivered) - a.lp.total_delivered) < 1e-9


def test_the_chosen_order_is_used_for_the_sequential_stages():
    for key in ("given", "cheap", "large", "best", "worst"):
        a = ev.analyse(_mcf(3), key)
        assert a.order_key == key and sorted(a.order) == [0, 1, 2] and abs(a.seq.objective - a.seq_by_order[a.order].objective) < 1e-9
    a = ev.analyse(_mcf(3), "best")
    b = ev.analyse(_mcf(3), "worst")
    assert a.seq.objective <= b.seq.objective


def test_verdict_codes_and_data():
    lvl, code, d = ev.verdict(ev.analyse(_mcf(3)))
    assert (lvl, code) == ("success", "integral") and not d["fractional"] and d["lp_delivered"] <= d["demand"] and d["ilp_cost"] == d["lp_cost"]
    assert d["n_binding"] == len(d["binding"]) and d["n_vars"] == 3 * ev.build("random", 3, *DEFAULT, C.DEFAULT_SEED).m and d["lagrange_err"] < 1e-6
    assert d["seq_loss"] >= -1e-9 and d["worst_loss"] >= d["best_loss"] >= -1e-9 and d["single_delivered"] >= d["lp_delivered"] - 1e-9
    lvl, code, d = ev.verdict(ev.analyse(md.gap_net()))
    assert (lvl, code) == ("warning", "fractional") and d["deliv_gap"] == 0.5 and d["n_fractional"] == 9
    lvl, code, d = ev.verdict(ev.analyse(md.generate_mcf(2, 6, 3, 20, 50, 90, 8, 3)))
    assert code in ("integral", "nothing") and d["lp_delivered"] <= d["demand"]


def test_distribution_is_consistent_with_single_runs():
    seeds = tuple(range(5))
    dist = ev.distribution(3, *DEFAULT, seeds=seeds)
    for i, seed in enumerate(seeds):
        mcf = md.generate_mcf(*DEFAULT, seed, 3)
        lp = sv.solve_lp(mcf)
        assert abs(dist["cols"]["lp_delivered"][i] - lp.total_delivered) < 1e-9 and dist["cols"]["n_vars"][i] == lp.n_vars
        assert abs(dist["seq_loss"]["given"][i] - (lp.total_delivered - sv.solve_sequential(mcf).total_delivered)) < 1e-9
    assert dist["n_seeds"] == 5 and 0 <= dist["share_fractional"] <= 1 and dist["lagrange_err_max"] < 1e-6 and "best_loss" in dist


def test_five_goods_skip_the_enumeration_of_all_orders():
    dist = ev.distribution(5, *DEFAULT, seeds=tuple(range(3)))
    assert "best_loss" not in dist and set(dist["seq_loss"]) == {"given", "cheap", "large"}


def test_pair_table_and_size_table_shapes():
    rows = ev.pair_table(families=((5, 55, 2), (6, 45, 3)), seeds=tuple(range(1, 21)))
    assert [r["family"] for r in rows] == [(5, 55, 2), (6, 45, 3)] and all(0 <= r["fractional"] <= r["n"] == 20 and r["ilp_worse"] <= r["fractional"] for r in rows)
    sz = ev.size_table(sizes=C.SCALE_SIZES[:2], ks=(2, 3), seeds=C.SCALE_SEEDS[:3])
    assert [(r["size"], r["K"]) for r in sz] == [(C.SCALE_SIZES[0], 2), (C.SCALE_SIZES[0], 3), (C.SCALE_SIZES[1], 2), (C.SCALE_SIZES[1], 3)]
    assert all(abs(r["vars"] - r["K"] * r["m"]) < 1e-9 for r in sz) and all(0 < s < 3 for s in ev.slopes(ev.size_table()).values())
