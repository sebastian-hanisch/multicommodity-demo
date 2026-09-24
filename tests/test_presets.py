"""Presets: vollständig, in den Grenzen, und jedes Beispielnetz zeigt, was sein Hilfetext behauptet."""

import pytest

import mcf_constants as C
import mcf_evaluation as ev
import mcf_presets as P

KEYS = set(P.PRESET_KEYS)


def _analyse(p):
    return ev.analyse(ev.build(p["net"], p["k"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"]), p["order"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["order"] in C.ORDER_LABELS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["density"] - C.DENSITY_MIN) % 10 == 0 and p["spread"] % 25 == 0 and (p["load"] - C.LOAD_MIN) % 10 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_random_net_preset():
    p = C.PRESETS["🚚 Zufallsnetz"]
    assert (p["net"], p["k"], p["order"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"]) == (
        C.DEFAULT_NET, C.DEFAULT_K, C.DEFAULT_ORDER, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)


def test_the_variant_presets_change_one_setting():
    base = C.PRESETS["🚚 Zufallsnetz"]
    for name, changed in (("🧊 Fünf Güter", ("k",)), ("📉 Schlechteste Reihenfolge", ("order",)), ("🏆 Beste Reihenfolge", ("order", "seed")), ("🏭 Werke knapp", ("load",)), ("🕸️ Dünnes Netz", ("density",))):
        assert all(C.PRESETS[name][k] == base[k] for k in base if k not in changed), name
    assert C.PRESETS["🧊 Fünf Güter"]["k"] == 5 and C.PRESETS["📉 Schlechteste Reihenfolge"]["order"] == "worst" and C.PRESETS["🏆 Beste Reihenfolge"]["order"] == "best"


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"🧩 Frachtnetz mit Bruch", "🧭 Reihenfolge-Falle"}


def test_default_net_is_a_typical_draw():
    """Das Beispielnetz (Seed 155, dasselbe wie in den Vorgänger-Demos) liefert 67 von 76 Einheiten, überlastet in den Einzellösungen 6 Kanten (Verteilung: 3,9 im Mittel, in 97 % mindestens eine) und hat 5 bindende Kanten."""
    p = C.PRESETS["🚚 Zufallsnetz"]
    dist = ev.distribution(p["k"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"])
    _, code, d = ev.verdict(_analyse(p))
    assert code == "integral" and 1 <= d["n_over"] <= 2 * dist["over_mean"] and 1 <= d["n_binding"] <= 2 * dist["binding_mean"] and p["seed"] == 155


def test_each_preset_shows_what_its_help_text_says():
    a = {name: _analyse(p) for name, p in C.PRESETS.items()}
    v = {name: ev.verdict(x) for name, x in a.items()}
    d = v["🚚 Zufallsnetz"][2]
    assert (d["lp_delivered"], d["demand"], d["lp_cost"], d["single_delivered"], d["n_over"], d["n_vars"], d["iterations"]) == (67.0, 76, 1548.0, 76.0, 6, 114, 40)
    k5 = v["🧊 Fünf Güter"][2]
    assert (k5["lp_delivered"], k5["lp_cost"], k5["seq_delivered"], k5["seq_loss"], k5["best_loss"]) == (76.0, 2234.0, 66.0, 10.0, 5.0)
    w = v["📉 Schlechteste Reihenfolge"][2]
    assert (w["seq_delivered"], w["seq_loss"], [a["📉 Schlechteste Reihenfolge"].mcf.names[k] for k in a["📉 Schlechteste Reihenfolge"].order]) == (51.0, 16.0, ["Trocken", "Kühl", "Frische"])
    b = v["🏆 Beste Reihenfolge"][2]
    assert (b["seq_loss"], b["worst_loss"], b["lp_delivered"], b["demand"]) == (0.0, 13.0, 77.0, 98)
    kn = v["🏭 Werke knapp"][2]
    assert (kn["lp_delivered"], kn["demand"], kn["single_delivered"], kn["n_over"]) == (67.0, 118, 105.0, 9)
    assert (v["🕸️ Dünnes Netz"][2]["lp_delivered"], v["🕸️ Dünnes Netz"][2]["single_delivered"]) == (45.0, 54.0)
    g = v["🧩 Frachtnetz mit Bruch"]
    assert g[1] == "fractional" and (g[2]["lp_delivered"], g[2]["ilp_delivered"]) == (1.5, 1.0)
    o = v["🧭 Reihenfolge-Falle"][2]
    assert (o["lp_delivered"], o["demand"], o["seq_delivered"]) == (4.0, 5, 3.0)


def test_the_presets_show_both_good_and_bad_news():
    """Gute Nachricht: fast überall ist das LP ganzzahlig; schlechte: die Güter nacheinander verlieren Lieferung, die Einzellösungen sind unzulässig, und im Frachtnetz mit Bruch ist das LP gebrochen."""
    a = {name: ev.verdict(_analyse(p)) for name, p in C.PRESETS.items()}
    assert sum(1 for x in a.values() if x[1] == "integral") == 7 and a["🧩 Frachtnetz mit Bruch"][1] == "fractional"
    assert all(x[2]["n_over"] >= 1 for x in a.values())
    assert any(x[2]["seq_loss"] > 0 for x in a.values())
