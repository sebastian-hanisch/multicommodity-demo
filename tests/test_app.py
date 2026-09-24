"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, alle Güter × Reihenfolgen, Randgrößen, Stufenregler, ausgeblendete Regler, Permalink, Experimente auf Abruf, Schlüssel und Achsensperre."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import mcf_constants as C
from mcf_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"

# Anfang der Meldung zum gezeigten Netz (Streamlit legt das führende Emoji in `icon`, nicht in `value`)
EXPECTED = {
    "🚚 Zufallsnetz": "Das LP ist ganzzahlig: 67 von 76 Einheiten für 1548; die Ganzzahligkeit kostet hier nichts. Zusammen ohne Rücksicht (jedes Gut allein) wären es 76 - dafür sind 6 gemeinsame Kanten überlastet. Die Güter nacheinander erreichen hier zufällig dasselbe.",
    "🧊 Fünf Güter": "Das LP ist ganzzahlig: 76 von 76 Einheiten für 2234; die Ganzzahligkeit kostet hier nichts. Zusammen ohne Rücksicht (jedes Gut allein) wären es 76 - dafür sind 5 gemeinsame Kanten überlastet. Die Güter nacheinander liefern 10 Einheiten weniger.",
    "📉 Schlechteste Reihenfolge": "Das LP ist ganzzahlig: 67 von 76 Einheiten für 1548; die Ganzzahligkeit kostet hier nichts. Zusammen ohne Rücksicht (jedes Gut allein) wären es 76 - dafür sind 6 gemeinsame Kanten überlastet. Die Güter nacheinander liefern 16 Einheiten weniger.",
    "🏆 Beste Reihenfolge": "Das LP ist ganzzahlig: 77 von 98 Einheiten für 1723; die Ganzzahligkeit kostet hier nichts. Zusammen ohne Rücksicht (jedes Gut allein) wären es 97 - dafür sind 6 gemeinsame Kanten überlastet. Die Güter nacheinander erreichen hier zufällig dasselbe.",
    "🏭 Werke knapp": "Das LP ist ganzzahlig: 67 von 118 Einheiten für 1290; die Ganzzahligkeit kostet hier nichts. Zusammen ohne Rücksicht (jedes Gut allein) wären es 105 - dafür sind 9 gemeinsame Kanten überlastet.",
    "🕸️ Dünnes Netz": "Das LP ist ganzzahlig: 45 von 76 Einheiten für 942; die Ganzzahligkeit kostet hier nichts. Zusammen ohne Rücksicht (jedes Gut allein) wären es 54 - dafür sind 5 gemeinsame Kanten überlastet. Die Güter nacheinander liefern 3 Einheiten weniger.",
    "🧩 Frachtnetz mit Bruch": "**Das LP ist gebrochen:** 9 Variablen sind nicht ganzzahlig (größter Bruch 0,50). Das LP liefert 1,5 Einheiten für 24, ganzzahlig gehen nur 1 für 15 - die Ganzzahligkeit kostet 0,5 Einheiten Lieferung.",
    "🧭 Reihenfolge-Falle": "Das LP ist ganzzahlig: 4 von 5 Einheiten für 30; die Ganzzahligkeit kostet hier nichts. Zusammen ohne Rücksicht (jedes Gut allein) wären es 4 - dafür ist 1 gemeinsame Kante überlastet. Die Güter nacheinander liefern 1 Einheit weniger.",
}
STAGES = {"🚚 Zufallsnetz": 6, "🧊 Fünf Güter": 8, "📉 Schlechteste Reihenfolge": 6, "🏆 Beste Reihenfolge": 6, "🏭 Werke knapp": 6, "🕸️ Dünnes Netz": 6, "🧩 Frachtnetz mit Bruch": 5, "🧭 Reihenfolge-Falle": 6}


def _run(setup=None, timeout=600):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _labels(at):
    return {w.label for w in list(at.sidebar.slider) + list(at.sidebar.selectbox) + list(at.sidebar.number_input) + list(at.sidebar.radio)}


def _texts(at):
    return [e.value for e in list(at.success) + list(at.warning) + list(at.info)]


def _has(at, prefix):
    return any(t.startswith(prefix) for t in _texts(at))


def _stage(at):
    return [s for s in at.slider if s.key == "mcf_stage"][0]


def _metric(at, label):
    return [m.value for m in at.metric if m.label == label]


def _captions(at):
    return [c.value for c in at.caption]


def test_default_renders_without_exception():
    at = _run()
    assert any("Vom Einzelgut zum gemeinsamen Modell" in m.value for m in at.markdown)
    assert _has(at, EXPECTED["🚚 Zufallsnetz"]) and not at.error
    assert _metric(at, "Lieferung (LP)")[0] == "67 von 76" and _metric(at, "Kosten (LP)")[0] == "1548" and _metric(at, "Nacheinander")[0] == "67 geliefert" and _metric(at, "Größe")[0] == "114 Variablen"
    assert _stage(at).value == 4 and _stage(at).max == 6                                   # Start auf dem gemeinsamen LP


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders_with_its_verdicts(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    assert _has(at, EXPECTED[name]), _texts(at)
    assert _stage(at).max == STAGES[name]
    if C.PRESETS[name]["net"] in C.FIXED_NETS:
        assert any(t.startswith("Festes Netz") for t in _texts(at))
    else:
        assert any(m.value.startswith("**Nicht nur dieses eine Netz:**") for m in at.markdown)


@pytest.mark.parametrize("order", list(C.ORDER_LABELS))
@pytest.mark.parametrize("K", range(C.K_MIN, C.K_MAX + 1))
def test_every_number_of_goods_and_order_renders(K, order):
    def setup(at):
        at.session_state["k_slider"] = K
        at.session_state["order_radio"] = order
    at = _run(setup)
    assert not at.error and _stage(at).max == K + 3 and _stage(at).value == K + 1
    assert any(t.startswith("Das LP ist ganzzahlig") for t in _texts(at))


def test_extreme_sizes_render():
    for p, d, s, dens, spread, load, K in ((C.P_MIN, C.D_MIN, C.S_MIN, C.DENSITY_MIN, C.SPREAD_MIN, C.LOAD_MIN, C.K_MIN), (C.P_MAX, C.D_MAX, C.S_MAX, C.DENSITY_MAX, C.SPREAD_MAX, C.LOAD_MAX, C.K_MAX),
                                           (C.P_MIN, C.D_MAX, C.S_MAX, C.DENSITY_MIN, C.SPREAD_MAX, C.LOAD_MAX, C.K_MAX), (C.P_MAX, C.D_MIN, C.S_MIN, C.DENSITY_MAX, C.SPREAD_MIN, C.LOAD_MIN, C.K_MIN)):
        def setup(at, vals=(p, d, s, dens, spread, load, K)):
            for key, value in zip(("p_slider", "d_slider", "s_slider", "density_slider", "spread_slider", "load_slider", "k_slider"), vals):
                at.session_state[key] = value
        at = _run(setup)
        assert not at.error and _stage(at).max == K + 3


def test_hidden_controls_follow_the_net():
    def labels_for(net):
        return _labels(_run(lambda a: a.session_state.__setitem__("net_select", net)))
    random_labels, fixed = labels_for("random"), labels_for("gap")
    assert {"Netz", "Reihenfolge beim Nacheinander", "Zahl der Güter", "Werke", "Verteilzentren", "Filialen", "Netzdichte [%]", "Streuung der Lane-Breiten [%]", "Auslastung [% der Werkskapazität]", "Zufalls-Seed"} <= random_labels
    assert fixed == {"Netz", "Reihenfolge beim Nacheinander"}                             # keine toten Regler bei festen Netzen


def test_hidden_slider_values_come_back_when_the_random_net_is_shown_again():
    at = _run(lambda a: (a.session_state.__setitem__("density_slider", 80), a.session_state.__setitem__("k_slider", 4)))
    at.session_state["net_select"] = "order"
    at.run()
    at.session_state["net_select"] = "random"
    at.run()
    assert not at.exception and at.slider(key="density_slider").value == 80 and at.slider(key="k_slider").value == 4


def test_stage_slider_shows_every_stage_with_its_caption():
    at = _run()
    needles = {0: "Jedes Gut bekommt seinen billigsten Fluss", 1: "Frische fährt auf der Restkapazität", 3: "Fertig:", 4: "Gemeinsames LP:", 5: "Ganzzahlig:", 6: "Mit den Schattenpreisen λ"}
    for k, needle in needles.items():
        _stage(at).set_value(k)
        at.run()
        assert not at.exception and any(needle in c for c in _captions(at)), (k, needle)
    at = _run(lambda a: _apply(a, C.PRESETS["🧩 Frachtnetz mit Bruch"]))
    assert any("Die Lösung ist gebrochen" in c for c in _captions(at))
    _stage(at).set_value(_stage(at).max - 1)
    at.run()
    assert any("die Ganzzahligkeit kostet 0,5 Einheiten Lieferung" in c for c in _captions(at))


def test_changing_the_net_resets_the_stage_to_the_lp():
    at = _run()
    _stage(at).set_value(1)
    at.run()
    assert _stage(at).value == 1
    at.session_state["k_slider"] = 5
    at.run()
    assert not at.exception and _stage(at).value == 6 and _stage(at).max == 8


def test_play_runs_through_all_frames_without_duplicate_chart_keys():
    """Beim Abspielen entstehen in einem Lauf mehrere Diagramme mit demselben Namen - die Schlüssel tragen deshalb die Stufe."""
    at = _run()
    [b for b in at.button if b.label == "▶️ Abspielen"][0].click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_permalink_parameters_are_clamped_and_snapped():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["density"] = "9999"
    at.query_params["spread"] = "abc"
    at.query_params["p"] = "-5"
    at.query_params["k"] = "9"
    at.run()
    assert not at.exception
    assert at.slider(key="density_slider").value == C.DENSITY_MAX and at.slider(key="spread_slider").value == C.DEFAULT_SPREAD and at.slider(key="p_slider").value == C.P_MIN and at.slider(key="k_slider").value == C.K_MAX
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["density"] = "63"
    at.query_params["spread"] = "60"
    at.query_params["load"] = "94"
    at.query_params["order"] = "worst"
    at.run()
    assert at.slider(key="density_slider").value == 60 and at.slider(key="spread_slider").value == 50 and at.slider(key="load_slider").value == 90 and at.radio(key="order_radio").value == "worst"


def test_unknown_values_in_the_permalink_fall_back_to_the_defaults():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["net"] = "ring"
    at.query_params["order"] = "lifo"
    at.query_params["k"] = "abc"
    at.run()
    assert not at.exception and at.selectbox(key="net_select").value == C.DEFAULT_NET
    assert at.radio(key="order_radio").value == C.DEFAULT_ORDER and at.slider(key="k_slider").value == C.DEFAULT_K


def test_randomize_moves_the_seed_but_not_the_distribution():
    at = _run()
    labels = ("LP gebrochen", "Nacheinander optimal", "Einzellösungen überlasten", "Bindende Kanten")
    pick = lambda a: [_metric(a, label) for label in labels]
    before = pick(at)
    seed_before = at.number_input(key="seed_input").value
    [b for b in at.sidebar.button if "Neues Netz" in b.label][0].click()
    at.run()
    assert not at.exception and at.number_input(key="seed_input").value != seed_before and pick(at) == before


def test_distribution_metrics_match_the_claims():
    at = _run()
    assert _metric(at, "LP gebrochen")[0] == "0 %" and _metric(at, "Nacheinander optimal")[0] == "5 %" and _metric(at, "Entkoppelte Flüsse überlastet")[0] == "69 %"
    assert _metric(at, "Entkopplung trifft den LP-Wert")[0] == "exakt"


def test_experiments_run_on_demand():
    at = _run()
    for text in ("Frachtnetze: zufällige gerichtete Graphen", "Mittel über 10 feste Netze je Zelle"):
        assert not any(text in c for c in _captions(at))
    for key in ("pairs_start", "size_start"):
        at.button(key=key).click()
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    text = " ".join(_captions(at))
    assert "Frachtnetze: zufällige gerichtete Graphen" in text and "1 von 700 Netzen sind gebrochen" in text
    assert "Mittel über 10 feste Netze je Zelle" in text and "Steigung im doppelt logarithmischen Diagramm 1,47" in text


def test_experiments_on_a_fixed_net_show_hints_instead_of_dead_controls():
    at = _run(lambda a: a.session_state.__setitem__("net_select", "gap"))
    assert not [b for b in at.button if b.key == "size_start"]
    assert sum("zufälliges Distributionsnetz wählen" in t for t in _texts(at)) >= 3


def _calls(src, name):
    """Der Text jedes Aufrufs `name(...)` einschließlich verschachtelter Klammern."""
    out = []
    for m in re.finditer(re.escape(name) + r"\(", src):
        depth, i = 1, m.end()
        while depth:
            depth += {"(": 1, ")": -1}.get(src[i], 0)
            i += 1
        out.append(src[m.start():i])
    return out


def test_every_plotly_chart_has_an_explicit_key_and_axes_are_locked():
    calls = _calls(APP.read_text(encoding="utf-8"), "plotly_chart")
    keys = [re.search(r'key=f?"([a-z_]+?)(?:_\{\w+\})?"', c).group(1) for c in calls]
    assert all(re.search(r'key=f?"[a-z_]+(_\{\w+\})?"', c) for c in calls), calls
    assert len(calls) == 4 and len(set(keys)) == 4 and keys == ["mcf_map", "stage_chart", "loss_chart", "size_chart"]
    viz = (ROOT / "mcf_visualization.py").read_text(encoding="utf-8")
    bodies = [b for b in viz.split(chr(10) + "def ") if b.startswith("build_")]
    assert "fixedrange=True" in viz and len(bodies) == 4 and all("_base(" in b or "_layout(" in b for b in bodies)


def test_app_text_has_no_links_to_repository_files():
    assert not re.search(r"\]\(\w+\.py\)", APP.read_text(encoding="utf-8"))


def test_footer_is_verbatim():
    src = APP.read_text(encoding="utf-8")
    assert "https://sebastianhanisch.net/kontakt.html" in src and "Interesse an einer maßgeschneiderten Lösung für" in src and "Operations Research und Machine Learning" in src


def test_runtime_needs_scipy_but_never_networkx():
    """Der LP-Löser ist HiGHS über scipy (Laufzeit); networkx bleibt reines Testorakel."""
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "scipy" in req and "networkx" not in req
    for path in ROOT.glob("*.py"):
        assert not re.search(r"^\s*(import|from)\s+networkx\b", path.read_text(encoding="utf-8"), re.M), path.name
