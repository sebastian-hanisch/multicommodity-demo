"""Jede Zahl, die README und Hilfetexte nennen, ist hier belegt (Standardeinstellungen, 100 feste Netze, Seeds 100000-100099)."""

import pytest

import mcf_constants as C
import mcf_evaluation as ev
import mcf_model as md
import mcf_solve as sv

S = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


@pytest.fixture(scope="module")
def dist():
    return ev.distribution(3, *S)


def test_the_lp_is_never_fractional_in_the_distribution_nets():
    """Vorab-Hypothese 'das LP wird oft gebrochen' widerlegt: 0 von 100 Netzen für 2, 3, 4 und 5 Güter; das ganzzahlige Programm ist nie schlechter."""
    for K in (2, 3, 4, 5):
        d = ev.distribution(K, *S)
        assert d["share_fractional"] == 0.0 and d["share_ilp_worse"] == 0.0 and d["n_seeds"] == 100


def test_fractional_freight_nets_are_rare():
    """Frachtnetze (Kapazität und Menge 1): in 6 von 7 Familien 0 gebrochene LPs von 100, in (8 Knoten, 30 %, 5 Güter) 1 - mit Lücke 0,5 Einheiten; in der Familie (5 Knoten, 55 %, 2 Güter) sind es 4 von 1500 Netzen."""
    rows = ev.pair_table()
    assert [r["fractional"] for r in rows] == [0, 0, 0, 0, 0, 0, 1] and [r["ilp_worse"] for r in rows] == [0, 0, 0, 0, 0, 0, 1] and rows[-1]["gap_max"] == 0.5
    count = 0
    for seed in range(1, 1501):
        mcf = md.generate_pairs(5, 55, 2, seed, 1, 1)
        lp = sv.solve_lp(mcf)
        count += bool(lp.fractional and sv.solve_ilp(mcf).objective > lp.objective + 1e-6)
    assert count == 4


def test_the_price_of_sharing(dist):
    """Jedes Gut allein: im Mittel 5,5 Einheiten mehr als das LP schafft, auf 3,9 gemeinsamen Kanten überlastet; in 97 von 100 Netzen mindestens eine Kante; 3,4 bindende Kanten im LP."""
    assert round(dist["single_overshoot_mean"], 2) == 5.47 and round(dist["over_mean"], 2) == 3.85 and sum(1 for o in dist["cols"]["over"] if o > 0) == 97
    assert round(dist["binding_mean"], 2) == 3.4 and round(dist["lp_delivered_mean"], 2) == 64.31 and round(dist["demand_mean"], 2) == 75.83


def test_sequential_solutions_lose_delivery(dist):
    """Drei Güter nacheinander: so viel wie das LP in 5 % (angegebene Reihenfolge), 9 % (billigstes zuerst), 7 % (größte zuerst); im Mittel fehlen 4,97 / 3,98 / 5,12 Einheiten; die beste Reihenfolge erreicht das LP in 18 %, die schlechteste ist in 97 % schlechter (im Mittel 1,21 bzw. 8,18 Einheiten fehlen)."""
    n = dist["n_seeds"]
    assert [round(100 * dist["share_seq_optimal"][k]) for k in ("given", "cheap", "large")] == [5, 9, 7]
    assert [round(sum(dist["seq_loss"][k]) / n, 2) for k in ("given", "cheap", "large")] == [4.97, 3.98, 5.12]
    assert (round(100 * dist["share_best_optimal"]), round(100 * dist["share_worst_bad"])) == (18, 97)
    assert (round(sum(dist["best_loss"]) / n, 2), round(sum(dist["worst_loss"]) / n, 2), max(dist["best_loss"]), max(dist["worst_loss"])) == (1.21, 8.18, 11.0, 24.0)


def test_sequential_solutions_across_the_number_of_goods():
    """Angegebene Reihenfolge, Anteil so gut wie das LP: 16 / 5 / 3 / 6 % für 2 / 3 / 4 / 5 Güter; fehlende Lieferung im Mittel 4,86 / 4,97 / 5,39 / 4,82."""
    res = {K: ev.distribution(K, *S) for K in (2, 3, 4, 5)}
    assert [round(100 * res[K]["share_seq_optimal"]["given"]) for K in (2, 3, 4, 5)] == [16, 5, 3, 6]
    assert [round(sum(res[K]["seq_loss"]["given"]) / 100, 2) for K in (2, 3, 4, 5)] == [4.86, 4.97, 5.39, 4.82]
    assert [round(100 * res[K]["share_best_optimal"]) for K in (2, 3, 4)] == [33, 18, 16] and "best_loss" not in res[5]


def test_the_decoupling_is_exact_but_not_feasible(dist):
    """Lagrange: Abweichung vom LP-Wert höchstens 1e-6 in allen Netzen; die entkoppelten Flüsse überlasten in 69 von 100 Netzen (2 / 3 / 4 / 5 Güter: 62 / 69 / 71 / 72 %) mindestens eine Kante."""
    assert dist["lagrange_err_max"] < 1e-6 and round(100 * dist["share_dec_over"]) == 69
    assert [round(100 * ev.distribution(K, *S)["share_dec_over"]) for K in (2, 4, 5)] == [62, 71, 72]


def test_lp_size_and_iterations(dist):
    """Drei Güter: 103 Variablen, 23 Iterationen im Mittel; 2 / 3 / 4 / 5 Güter: 69 / 103 / 137 / 172 Variablen, 18,3 / 23,0 / 26,5 / 30,4 Iterationen; Steigung der Iterationen gegen die Variablen 1,47."""
    assert round(dist["n_vars_mean"]) == 103 and round(dist["iterations_mean"]) == 23
    res = {K: ev.distribution(K, *S) for K in (2, 4, 5)}
    assert [round(res[K]["n_vars_mean"]) for K in (2, 4, 5)] == [69, 137, 172] and [round(res[K]["iterations_mean"], 1) for K in (2, 4, 5)] == [18.3, 26.5, 30.4]
    assert round(ev.slopes(ev.size_table())["nit"], 2) == 1.47


def test_default_net_numbers():
    d = ev.verdict(ev.analyse(ev.build("random", 3, *S, C.DEFAULT_SEED)))[2]
    assert (d["lp_delivered"], d["demand"], d["lp_cost"], d["ilp_cost"], d["single_delivered"], d["n_over"], d["n_binding"], d["iterations"], d["n_vars"], d["dec_over"]) == (67.0, 76, 1548.0, 1548.0, 76.0, 6, 5, 40, 114, 2)
    assert (d["seq_delivered"], d["seq_cost"], d["seq_loss"], d["best_loss"], d["worst_loss"]) == (67.0, 1610.0, 0.0, 0.0, 16.0)
    w = ev.verdict(ev.analyse(ev.build("random", 3, *S, C.DEFAULT_SEED), "worst"))[2]
    assert (w["seq_delivered"], w["seq_loss"], w["order"]) == (51.0, 16.0, (1, 2, 0))


def test_preset_numbers():
    k5 = ev.verdict(ev.analyse(ev.build("random", 5, *S, C.DEFAULT_SEED)))[2]
    assert (k5["lp_delivered"], k5["demand"], k5["lp_cost"], k5["seq_delivered"], k5["seq_loss"], k5["best_loss"], k5["worst_loss"]) == (76.0, 76, 2234.0, 66.0, 10.0, 5.0, 23.0)
    s101 = ev.verdict(ev.analyse(ev.build("random", 3, *S[:5], 90, 101), "best"))[2]
    assert (s101["lp_delivered"], s101["demand"], s101["best_loss"], s101["worst_loss"]) == (77.0, 98, 0.0, 13.0) and ev.verdict(ev.analyse(ev.build("random", 3, *S[:5], 90, 101)))[2]["seq_loss"] == 6.0
    knapp = ev.verdict(ev.analyse(ev.build("random", 3, 3, 3, 8, 60, 50, 140, C.DEFAULT_SEED)))[2]
    assert (knapp["lp_delivered"], knapp["demand"], knapp["single_delivered"], knapp["n_over"]) == (67.0, 118, 105.0, 9)
    thin = ev.verdict(ev.analyse(ev.build("random", 3, 3, 3, 8, 30, 50, 90, C.DEFAULT_SEED)))[2]
    assert (thin["lp_delivered"], thin["demand"], thin["single_delivered"]) == (45.0, 76, 54.0)


def test_the_freight_nets():
    g = ev.verdict(ev.analyse(md.gap_net()))
    assert g[1] == "fractional" and (g[2]["lp_delivered"], g[2]["lp_cost"], g[2]["ilp_delivered"], g[2]["ilp_cost"], g[2]["n_fractional"], g[2]["max_fraction"]) == (1.5, 24.0, 1.0, 15.0, 9, 0.5)
    o = ev.analyse(md.order_net())
    d = ev.verdict(o)[2]
    assert (d["lp_delivered"], d["demand"], d["best_loss"], d["worst_loss"]) == (4.0, 5, 0.0, 1.0) and sorted(s.total_delivered for s in o.seq_by_order.values()) == [3.0, 3.0, 3.0, 4.0, 4.0, 4.0]
    assert ev.analyse(md.order_net(), "worst").seq.total_delivered == 3.0 and ev.analyse(md.order_net(), "best").seq.total_delivered == 4.0
