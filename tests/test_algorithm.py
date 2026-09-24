"""Kern: das Mehrgüter-Modell gegen unabhängige Gegenproben (networkx für ein Gut, Brute Force für zwei Güter, HiGHS dual-simplex gegen Innere-Punkte-Verfahren), Zulässigkeit je Lösung,
Lagrange-Entkopplung (starke Dualität, unabhängig über SSP), komplementärer Schlupf, Reihenfolge-Verfahren, gebrochene und ganzzahlige Beispielnetze."""

import itertools
import random

import networkx as nx
import numpy as np
import pytest

import mcf_constants as C
import mcf_model as md
import mcf_scenario as sc
import mcf_solve as sv
import mcf_ssp as ssp
from mcf_scenario import SplitMix64

TOL = 1e-6


def _models(count):
    """Zufällige Distributionsnetze mit 2 bis 4 Gütern in verschiedenen Größen."""
    rng = random.Random(21)
    sizes = ((2, 2, 3), (3, 3, 6), (3, 3, 8), (4, 3, 5), (2, 4, 9))
    for i in range(count):
        p, d, s = sizes[i % len(sizes)]
        yield md.generate_mcf(p, d, s, rng.choice((40, 60, 80, 100)), rng.choice((0, 50, 100)), rng.choice((60, 90, 130)), 4000 + i, 2 + i % 3)


def _pairs(count, n=5, K=2):
    for seed in range(1, count + 1):
        yield md.generate_pairs(n, 55, K, seed, 2, 2)


def _check_feasible(mcf, x, tol=TOL):
    """Erhaltung je Gut, gemeinsame Kapazität, gutspezifische Obergrenzen, Nichtnegativität."""
    net = mcf.net
    assert (x >= -tol).all()
    for k in range(mcf.K):
        bal = np.zeros(net.n)
        for e, (u, v, _, _, _) in enumerate(net.arcs):
            bal[u] -= x[k, e]
            bal[v] += x[k, e]
            assert x[k, e] <= min(mcf.ub[k][e], 10 ** 6) + tol
        assert all(abs(bal[v]) <= tol for v in range(net.n) if v not in (net.s, net.t))
    for e, (_, _, cap, _, _) in enumerate(net.arcs):
        if mcf.joint[e]:
            assert x[:, e].sum() <= cap + tol


def test_splitmix64_reference_vector():
    rng = SplitMix64(0)
    assert [rng.next() for _ in range(2)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4]


def test_the_ssp_copy_reproduces_the_predecessor_numbers():
    """Wache: SSP 53 907 durchsuchte Kanten (Mittel 539,07) über die 100 festen Netze der Vorgänger-Demos, Kosten = networkx."""
    scans = 0
    for seed in C.DIST_SEEDS:
        net = sc.generate(3, 3, 8, 60, 50, 90, seed)
        r = ssp.ssp(net, keep_trace=False)
        scans += r.scanned_total
        if seed < C.DIST_SEEDS[0] + 20:
            g = nx.DiGraph()
            for u, v, c, k, _ in net.arcs:
                g.add_edge(u, v, capacity=c, weight=k)
            flow = nx.max_flow_min_cost(g, net.s, net.t)
            assert (r.value, r.total) == (sum(flow[net.s].values()), nx.cost_of_flow(g, flow))
    assert scans == 53907


def test_the_model_has_the_documented_structure():
    for mcf in _models(10):
        net = mcf.net
        assert mcf.K == len(mcf.names) == len(mcf.factors) == len(mcf.ub) and mcf.M == md.M_REWARD
        assert all(len(row) == mcf.m for row in mcf.ub)
        supply = [e for e, a in enumerate(net.arcs) if a[4] == sc.K_SUPPLY]
        assert all(any(mcf.ub[k][e] > 0 for e in supply) for k in range(mcf.K))                              # jedes Gut hat ein Werk
        demand_arcs = [e for e, a in enumerate(net.arcs) if a[4] == sc.K_DEMAND]
        assert all(sum(mcf.ub[k][e] for k in range(mcf.K)) == net.arcs[e][2] for e in demand_arcs)          # Nachfrage wird ganz auf die Güter verteilt
        assert mcf.joint == tuple(a[4] != sc.K_DEMAND for a in net.arcs) and mcf.reward == tuple(a[1] == net.t for a in net.arcs)
        assert mcf.total_demand() == sum(net.arcs[e][2] for e in demand_arcs)
        assert all(mcf.cost(k, e) == mcf.factors[k] * net.arcs[e][3] for k in range(mcf.K) for e in range(mcf.m) if net.arcs[e][4] in (sc.K_LANE_IN, sc.K_LANE_OUT))


def test_generation_is_reproducible_and_seed_dependent():
    assert md.generate_mcf(3, 3, 8, 60, 50, 90, 5, 3) == md.generate_mcf(3, 3, 8, 60, 50, 90, 5, 3) != md.generate_mcf(3, 3, 8, 60, 50, 90, 6, 3)
    assert md.generate_pairs(5, 55, 2, 3) == md.generate_pairs(5, 55, 2, 3) != md.generate_pairs(5, 55, 2, 4)


def test_one_good_equals_the_single_commodity_optimum():
    """K = 1: Lieferung und Kosten des LP sind größter Fluss und billigster Fluss von networkx (das Ein-Gut-Netz mit den Obergrenzen des Guts)."""
    for seed in range(20):
        mcf = md.generate_mcf(3, 3, 8, 60, 50, 90, 6000 + seed, 1)
        lp = sv.solve_lp(mcf)
        g = nx.DiGraph()
        for e, (u, v, cap, cost, _) in enumerate(mcf.net.arcs):
            c = min(cap, mcf.ub[0][e])
            if c > 0:
                g.add_edge(u, v, capacity=c, weight=mcf.cost(0, e))
        flow = nx.max_flow_min_cost(g, mcf.net.s, mcf.net.t)
        assert abs(lp.total_delivered - sum(flow[mcf.net.s].values())) < TOL and abs(lp.cost - nx.cost_of_flow(g, flow)) < TOL
        _check_feasible(mcf, lp.x)


def test_lp_solutions_are_feasible_and_ilp_is_integral_and_never_better():
    for mcf in list(_models(15)) + list(_pairs(15, 5, 3)):
        lp, ilp = sv.solve_lp(mcf), sv.solve_ilp(mcf)
        _check_feasible(mcf, lp.x)
        _check_feasible(mcf, ilp.x)
        assert np.allclose(ilp.x, np.round(ilp.x)) and ilp.objective >= lp.objective - TOL
        assert lp.n_vars == mcf.K * mcf.m and lp.n_eq == mcf.K * (mcf.net.n - 2) and lp.n_ub == sum(mcf.joint)


def test_the_interior_point_method_agrees_with_the_simplex_method():
    for mcf in list(_models(10)):
        assert abs(sv.solve_lp(mcf, "highs-ds").objective - sv.solve_lp(mcf, "highs-ipm").objective) < 1e-4


def _brute_force(mcf):
    """Ganzzahliger Optimalwert (Kosten - M·Lieferung) durch Aufzählung aller 0/1-Flüsse je Gut auf den Kanten (nur Kleinstnetze mit Kapazität und Menge 1)."""
    m, K = mcf.m, mcf.K
    net = mcf.net
    best = None
    per_good = []
    for k in range(K):
        options = []
        for bits in itertools.product((0, 1), repeat=m):
            if any(bits[e] > mcf.ub[k][e] for e in range(m)):
                continue
            bal = [0] * net.n
            for e, (u, v, _, _, _) in enumerate(net.arcs):
                bal[u] -= bits[e]
                bal[v] += bits[e]
            if all(bal[v] == 0 for v in range(net.n) if v not in (net.s, net.t)):
                options.append(bits)
        per_good.append(options)
    for combo in itertools.product(*per_good):
        if any(sum(combo[k][e] for k in range(K)) > net.arcs[e][2] for e in range(m) if mcf.joint[e]):
            continue
        obj = sum((-mcf.M if mcf.reward[e] else mcf.cost(k, e)) * combo[k][e] for k in range(K) for e in range(m))
        best = obj if best is None or obj < best else best
    return best


def test_brute_force_on_the_small_freight_nets():
    for seed in (1341, 813, 568, 2, 3, 4):
        mcf = md.generate_pairs(5, 55, 2, seed, 1, 1)
        if mcf.m > 15:
            continue
        assert abs(sv.solve_ilp(mcf).objective - _brute_force(mcf)) < TOL, seed
    gap = md.gap_net()
    assert abs(sv.solve_ilp(gap).objective - _brute_force(gap)) < TOL


def test_the_gap_net_has_a_fractional_lp_and_the_order_net_does_not():
    gap = md.gap_net()
    lp, ilp = sv.solve_lp(gap), sv.solve_ilp(gap)
    assert lp.fractional and lp.n_fractional == 9 and abs(lp.max_fraction - 0.5) < TOL
    assert (lp.total_delivered, lp.cost, ilp.total_delivered, ilp.cost) == (1.5, 24.0, 1.0, 15.0) and lp.objective < ilp.objective
    order = md.order_net()
    lp2 = sv.solve_lp(order)
    assert not lp2.fractional and (lp2.total_delivered, lp2.cost) == (4.0, 30.0)


def test_duals_are_non_negative_and_complementary():
    """Komplementärer Schlupf: ein positiver Schattenpreis nur auf ausgelasteten gemeinsamen Kanten; auf nicht gemeinsamen Kanten 0."""
    for mcf in list(_models(15)) + list(_pairs(10, 6, 3)):
        lp = sv.solve_lp(mcf)
        assert (lp.duals >= 0).all()
        for e, (_, _, cap, _, _) in enumerate(mcf.net.arcs):
            if lp.duals[e] > TOL:
                assert mcf.joint[e] and abs(lp.x[:, e].sum() - cap) < TOL


def test_lagrange_decoupling_hits_the_lp_optimum_exactly():
    """Mit den Schattenpreisen gilt sum_k (Min-Cost-Flow von Gut k mit Kosten c + lambda) - sum lambda·u = LP-Wert (starke Dualität, über SSP unabhängig nachgerechnet)."""
    for mcf in list(_models(25)) + list(_pairs(15, 6, 3)):
        lp = sv.solve_lp(mcf)
        value, flows = sv.decouple(mcf, lp.duals)
        assert abs(value - lp.objective) < 1e-6 * max(1.0, abs(lp.objective)), (value, lp.objective)
        for k, flow in enumerate(flows):
            assert all(0 <= flow[e] <= mcf.ub[k][e] for e in range(mcf.m))


def test_any_prices_give_a_lower_bound():
    """Schwache Dualität: für beliebige Preise lambda >= 0 ist L(lambda) höchstens das LP-Optimum."""
    rng = random.Random(5)
    for mcf in list(_models(10)):
        lp = sv.solve_lp(mcf)
        for _ in range(3):
            lam = [rng.choice((0, 0, 1, 3, 10)) if mcf.joint[e] else 0 for e in range(mcf.m)]
            value, _ = sv.decouple(mcf, lam)
            assert value <= lp.objective + 1e-6


def test_independent_solutions_are_a_lower_bound_and_overload_edges():
    overloaded = 0
    for mcf in list(_models(25)):
        lp = sv.solve_lp(mcf)
        single, over = sv.solve_single(mcf)
        assert single.objective <= lp.objective + TOL and single.total_delivered >= lp.total_delivered - TOL
        caps = [a[2] for a in mcf.net.arcs]
        assert set(over) == {e for e in range(mcf.m) if mcf.joint[e] and single.x[:, e].sum() > caps[e]}
        overloaded += bool(over)
    assert overloaded >= 15


def test_sequential_solutions_are_feasible_and_never_better_than_the_lp():
    for mcf in list(_models(20)) + list(_pairs(15, 6, 3)):
        lp = sv.solve_lp(mcf)
        for order in itertools.islice(itertools.permutations(range(mcf.K)), 6):
            seq = sv.solve_sequential(mcf, order)
            _check_feasible(mcf, seq.x)
            assert seq.objective >= lp.objective - TOL


def test_the_order_matters_on_the_order_net():
    mcf = md.order_net()
    res = {o: sv.solve_sequential(mcf, o).total_delivered for o in itertools.permutations(range(3))}
    assert sorted(res.values()) == [3.0, 3.0, 3.0, 4.0, 4.0, 4.0] and sv.solve_lp(mcf).total_delivered == 4.0


def test_a_single_good_needs_no_order():
    mcf = md.generate_mcf(3, 3, 8, 60, 50, 90, 155, 1)
    lp = sv.solve_lp(mcf)
    seq = sv.solve_sequential(mcf)
    assert abs(seq.objective - lp.objective) < TOL


def test_the_model_solves_an_unreachable_net_with_zero_delivery():
    mcf = md.generate_mcf(2, 6, 3, 20, 50, 90, 8, 3)
    lp = sv.solve_lp(mcf)
    assert lp.status == "optimal" and lp.total_delivered >= 0 and not lp.fractional


def test_the_lp_size_grows_linearly_in_the_number_of_goods():
    sizes = [sv.solve_lp(md.generate_mcf(3, 3, 8, 60, 50, 90, 155, K)).n_vars for K in (1, 2, 3, 4, 5)]
    m = md.generate_mcf(3, 3, 8, 60, 50, 90, 155, 1).m
    assert sizes == [K * m for K in (1, 2, 3, 4, 5)]
