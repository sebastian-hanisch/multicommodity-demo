"""Unabhängiges Orakel für das Mehrgüter-Modell auf zufälligen kleinen Netzen (Distributionsnetze mit 1 bis 4 Gütern und Frachtnetze mit Quelle-Ziel-Paaren):
- Jedes Gut allein, jeder Schritt von „nacheinander“ und die Lagrange-Funktion zu den Schattenpreisen werden mit einem eigenen Ein-Gut-LP (scipy.optimize.linprog) nachgerechnet, ohne die SSP-Kopie.
  Starke Dualität: Summe der Ein-Gut-Optima mit Kosten c + λ minus Σ λ·u ist gleich dem LP-Wert; die Preise sind ≥ 0 und nur auf vollen Kanten positiv.
- LP und ganzzahliges Programm gegen OR-Tools (GLOP bzw. CP-SAT), wenn installiert.
Gleichstände: das Ergebnis von „nacheinander“ hängt bei mehreren Optima vom Verfahren ab, darum wird jeder Schritt auf Optimalität für die Restkapazität geprüft, nicht das Gesamtergebnis verglichen."""

import random

import numpy as np
import pytest
from scipy.optimize import linprog

import mcf_model as md
import mcf_solve as sv

TOL = 1e-6


def _single_good_lp(mcf, k, cap, extra=None):
    """Kleinster Wert von Kosten − M · Lieferung für Gut k allein (Kapazität min(Obergrenze, cap, Nachfrage des Guts)); `extra`: zusätzliche Kosten je Kante."""
    net, m = mcf.net, mcf.m
    a = np.zeros((net.n, m))
    for e, (u, v, *_rest) in enumerate(net.arcs):
        a[u, e] += 1
        a[v, e] -= 1
    inner = [v for v in range(net.n) if v not in (net.s, net.t)]
    c = np.array([(-mcf.M if mcf.reward[e] else mcf.cost(k, e)) + (extra[e] if extra else 0) for e in range(m)], float)
    dk = mcf.demand(k)
    res = linprog(c, A_eq=a[inner], b_eq=np.zeros(len(inner)), bounds=[(0, min(mcf.ub[k][e], cap[e], dk)) for e in range(m)], method="highs")
    assert res.status == 0
    return res.fun


def _value(mcf, k, x):
    return sum(mcf.cost(k, e) * x[k, e] for e in range(mcf.m) if not mcf.reward[e]) - mcf.M * sum(x[k, e] for e in range(mcf.m) if mcf.reward[e])


def _instances(rng):
    for _ in range(14):
        yield md.generate_mcf(rng.randint(2, 4), rng.randint(2, 4), rng.randint(3, 7), rng.choice((30, 60, 100)), rng.choice((0, 50, 100)), rng.choice((60, 90, 140)), rng.randint(1, 10 ** 6), rng.randint(1, 4))
    for _ in range(14):
        yield md.generate_pairs(rng.randint(4, 6), rng.choice((35, 50, 70)), rng.randint(2, 3), rng.randint(1, 10 ** 6), rng.choice((1, 2)), rng.choice((1, 2)))


def test_single_sequential_and_lagrangian_against_own_single_good_lps():
    rng = random.Random(20261004)
    for mcf in _instances(rng):
        caps = [a[2] for a in mcf.net.arcs]
        lp = sv.solve_lp(mcf)
        for e in range(mcf.m):                                                       # Preise: ≥ 0, nur auf vollen gemeinsamen Kanten
            assert lp.duals[e] >= -TOL
            assert lp.duals[e] <= TOL or (mcf.joint[e] and abs(lp.x[:, e].sum() - caps[e]) < TOL)
        lam = [float(d) if mcf.joint[e] else 0.0 for e, d in enumerate(lp.duals)]
        lagrange = sum(_single_good_lp(mcf, k, [10 ** 6] * mcf.m, lam) for k in range(mcf.K)) - sum(lam[e] * caps[e] for e in range(mcf.m) if mcf.joint[e])
        assert abs(lagrange - lp.objective) < 1e-4                                   # starke Dualität
        assert abs(sv.decouple(mcf, lp.duals)[0] - lp.objective) < 1e-4
        single, _ = sv.solve_single(mcf)
        for k in range(mcf.K):
            assert abs(_value(mcf, k, single.x) - _single_good_lp(mcf, k, caps)) < 1e-4
        for order in (tuple(range(mcf.K)), tuple(reversed(range(mcf.K)))):
            seq = sv.solve_sequential(mcf, order)
            left = list(caps)
            for k in order:
                assert abs(_value(mcf, k, seq.x) - _single_good_lp(mcf, k, left)) < 1e-4      # jedes Gut optimal auf der Restkapazität
                left = [left[e] - (seq.x[k, e] if mcf.joint[e] else 0) for e in range(mcf.m)]
            assert all(x >= -TOL for x in left) and seq.objective >= lp.objective - TOL and seq.total_delivered <= lp.total_delivered + TOL


def test_lp_and_integer_program_against_ortools():
    pywraplp = pytest.importorskip("ortools.linear_solver.pywraplp")
    cp_model = pytest.importorskip("ortools.sat.python.cp_model")
    rng = random.Random(7)
    for mcf in _instances(rng):
        net, m, K = mcf.net, mcf.m, mcf.K
        cost = [[mcf.cost(k, e) for e in range(m)] for k in range(K)]

        def lp_value():
            def stage(first, delivered=None):
                s = pywraplp.Solver.CreateSolver("GLOP")
                x = [[s.NumVar(0, mcf.ub[k][e] if mcf.ub[k][e] < 10 ** 6 else s.infinity(), "") for e in range(m)] for k in range(K)]
                for k in range(K):
                    for v in range(net.n):
                        if v not in (net.s, net.t):
                            s.Add(sum(x[k][e] for e in range(m) if net.arcs[e][1] == v) == sum(x[k][e] for e in range(m) if net.arcs[e][0] == v))
                for e in range(m):
                    if mcf.joint[e]:
                        s.Add(sum(x[k][e] for k in range(K)) <= net.arcs[e][2])
                deliv = sum(x[k][e] for k in range(K) for e in range(m) if mcf.reward[e])
                if first:
                    s.Maximize(deliv)
                else:
                    s.Add(deliv >= delivered - 1e-7)
                    s.Minimize(sum(cost[k][e] * x[k][e] for k in range(K) for e in range(m) if not mcf.reward[e]))
                assert s.Solve() == pywraplp.Solver.OPTIMAL
                return s.Objective().Value()
            d = stage(True)
            return stage(False, d) - mcf.M * d

        lp = sv.solve_lp(mcf)
        assert abs(lp.objective - lp_value()) < 1e-4

        model = cp_model.CpModel()
        x = [[model.NewIntVar(0, min(mcf.ub[k][e], 10 ** 4), "") for e in range(m)] for k in range(K)]
        for k in range(K):
            for v in range(net.n):
                if v not in (net.s, net.t):
                    model.Add(sum(x[k][e] for e in range(m) if net.arcs[e][1] == v) == sum(x[k][e] for e in range(m) if net.arcs[e][0] == v))
        for e in range(m):
            if mcf.joint[e]:
                model.Add(sum(x[k][e] for k in range(K)) <= net.arcs[e][2])
        model.Minimize(sum(cost[k][e] * x[k][e] for k in range(K) for e in range(m) if not mcf.reward[e]) - mcf.M * sum(x[k][e] for k in range(K) for e in range(m) if mcf.reward[e]))
        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 1
        assert solver.Solve(model) == cp_model.OPTIMAL
        ilp = sv.solve_ilp(mcf)
        assert abs(ilp.objective - solver.ObjectiveValue()) < 1e-4 and ilp.objective >= lp.objective - TOL


def test_teaching_nets_against_hand_values():
    """Frachtnetz mit Bruch: LP 1,5 Einheiten für 24, ganzzahlig 1 für 15; Reihenfolge-Falle: LP 4 von 5 für 30, drei der sechs Reihenfolgen liefern 3."""
    gap = md.gap_net()
    lp, ilp = sv.solve_lp(gap), sv.solve_ilp(gap)
    assert (lp.total_delivered, lp.cost, ilp.total_delivered, ilp.cost) == (1.5, 24.0, 1.0, 15.0) and lp.fractional
    order = md.order_net()
    assert (sv.solve_lp(order).total_delivered, sv.solve_lp(order).cost) == (4.0, 30.0)
    import itertools
    assert sorted(sv.solve_sequential(order, o).total_delivered for o in itertools.permutations(range(3))) == [3.0, 3.0, 3.0, 4.0, 4.0, 4.0]
