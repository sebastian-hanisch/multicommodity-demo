"""Mehrgüterfluss - Güter teilen sich die Kanten - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Modell - das Kanten-LP des Mehrgüterflusses - und lässt stattdessen das Beispiel wachsen.
Siebtes Stück der Netzwerkfluss-Linie der "Konzepte"-Reihe, Beginn des Mehrgüter-Asts: mehrere Güter teilen sich Kapazitäten, und die Ein-Gut-Verfahren der ersten Stücke reichen nicht mehr. Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import mcf_constants as C
import mcf_evaluation as ev
from mcf_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sync_query_params,
)
from mcf_visualization import (
    build_loss_hist,
    build_mcf,
    build_size,
    build_stages,
)

st.set_page_config(page_title="Mehrgüterfluss – Sebastian Hanisch", layout="wide")

HEUR_SHORT = {"given": "wie angegeben", "cheap": "billigstes zuerst", "large": "größte Nachfrage zuerst"}


def _pct(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f} %".replace(".", ",")


def _share(x):
    """Anteil (0..1) als 'nn %'."""
    return f"{100 * x:.0f} %"


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _u(x):
    """Menge: ganze Zahl ohne Nachkommastellen, sonst eine."""
    return f"{round(x)}" if abs(x - round(x)) < 1e-6 else _f(x, 1)


def _units(x):
    return "1 Einheit" if abs(x - 1) < 1e-6 else f"{_u(x)} Einheiten"


def _edges(n):
    return "1 gemeinsame Kante" if n == 1 else f"{n} gemeinsame Kanten"


def _int(x):
    return f"{int(round(x)):,}".replace(",", " ")


@st.cache_resource(show_spinner=False, max_entries=32)
def _analysis(params, K, order):
    return ev.analyse(ev.build(params[0], K, *params[1:]), order)


st.title("📦 Mehrgüterfluss – Güter teilen sich die Kanten")
st.markdown(
    """
In den ersten sechs Stücken war alles **ein Gut**: ein Fluss, ein Preis je Einheit, und Successive Shortest Paths fand den billigsten Fluss. Jetzt fahren **mehrere Güter** - Frische, Trocken, Kühl - über dieselben Lanes und Verteilzentren; die Kapazität gilt für die **Summe**.
Jedes Gut für sich mit dem billigsten Fluss zu versorgen, geht dann nicht mehr auf: zusammen überschreiten die Flüsse die Kanten. Die Güter **nacheinander** zu fahren ist zulässig, aber die Reihenfolge entscheidet. Das **gemeinsame LP** (eine Variable je Gut und Kante) ist optimal und liefert **Schattenpreise** der gemeinsamen Kapazitäten -
und mit diesen Preisen sind die Güter wieder **unabhängige** Ein-Gut-Flüsse. Diese Demo zeigt die Stufen vom Einzelgut zum gemeinsamen Modell, wann das LP **gebrochen** wird (die totale Unimodularität geht verloren, ganzzahliger Mehrgüterfluss ist NP-schwer) - und dass das im Alltag erstaunlich selten passiert.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - siebtes Stück der Netzwerkfluss-Linie der \"Konzepte\"-Reihe, Beginn des Mehrgüter-Asts - **ein** Modell an einem wachsenden Beispiel. "
    "Die Folgestücke setzen an den Schwächen an: die **Pfad-Formulierung mit Column Generation** gegen die Größe des Kanten-LP, **Garg–Könemann** (Näherung mit Preisen) und das **Netzwerkdesign mit Fixkosten** (Benders-Zerlegung, Slope Scaling)."
)

with st.expander("So funktioniert das Mehrgüter-LP", expanded=True):
    st.markdown(
        r"""
1. **Variablen:** $x_{k,e}\ge 0$ - wie viel von Gut $k$ über Kante $e$ fließt. Bei $K$ Gütern und $m$ Kanten sind das $K\cdot m$ Variablen.
2. **Flusserhaltung** je Gut und Knoten: was hineinfließt, fließt hinaus (Quelle und Senke ausgenommen). Jedes Gut hat seine eigenen Werke (nicht jedes Werk stellt jedes Gut her) und seine eigene Nachfrage je Filiale.
3. **Gemeinsame Kapazität:** $\sum_k x_{k,e}\le u_e$ auf Werks-, Lane- und Verteilzentrumkanten - die Kopplung, die die Güter aneinander bindet.
4. **Ziel:** so viel wie möglich liefern (Belohnung $M$ je Einheit), darunter so billig wie möglich. Kosten je Gut: Lanes mal Kostenfaktor (Kühl teurer als Trocken).
5. **Schattenpreise:** die Duallösung $\lambda_e\ge 0$ der gemeinsamen Kapazitäten. Bindende Kanten sind die Engstellen; $\lambda_e$ ist der Wert einer zusätzlichen Einheit Kapazität.
6. **Entkopplung:** mit Preisen $\lambda$ sind die Kosten $c_{k,e}+\lambda_e$; jedes Gut ist dann ein gewöhnlicher Min-Cost-Flow (SSP). Die Summe der $K$ Werte minus $\sum_e\lambda_e u_e$ ist der LP-Wert (Lagrange-Dualität).
7. **Ganzzahligkeit:** anders als beim Ein-Gut-Fluss ist die Matrix nicht mehr total unimodular - das LP *kann* gebrochene Ecken haben, ganzzahlig lösen ist NP-schwer.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielnetz laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Netz", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
        help="Ein zufälliges Distributionsnetz mit mehreren Gütern, oder eines der festen Frachtnetze: das mit Bruch (das LP liefert 1,5 Einheiten, ganzzahlig nur 1) und das, in dem die Reihenfolge entscheidet.",
    )
    order = st.radio(
        "Reihenfolge beim Nacheinander", list(C.ORDER_LABELS), key="order_radio", format_func=lambda k: C.ORDER_LABELS[k],
        help="In welcher Reihenfolge die Güter nacheinander auf die Restkapazität fahren. Billigstes zuerst = kleinster Kostenfaktor; beste und schlechteste Reihenfolge werden durch Aufzählung aller Reihenfolgen gefunden (bei fünf Gütern 120).",
    )
    if net_key == "random":
        seed_widget("k_slider")
        K = st.slider("Zahl der Güter", *bounds("k_slider"), key="k_slider", help="Frische, Trocken, Kühl, Getränke, Tiefkühl (in dieser Reihenfolge); Kostenfaktor auf den Lanes 2, 1, 3, 1, 4. Jedes Werk stellt ein Gut mit 70 % Wahrscheinlichkeit her, die Nachfrage der Filialen wird zufällig auf die Güter verteilt.")
        st.session_state[KEPT["k_slider"]] = K
        seed_widget("p_slider")
        p = st.slider("Werke", *bounds("p_slider"), key="p_slider", help="Anzahl der Werke (oben im Netz); Kosten je Einheit 1 bis 5.")
        st.session_state[KEPT["p_slider"]] = p
        seed_widget("d_slider")
        d = st.slider("Verteilzentren", *bounds("d_slider"), key="d_slider", help="Anzahl der Verteilzentren; Umschlagkosten 1 bis 3 je Einheit, Durchsatz 30 bis 60 % der gesamten Werkskapazität (gemeinsam für alle Güter).")
        st.session_state[KEPT["d_slider"]] = d
        seed_widget("s_slider")
        s = st.slider("Filialen", *bounds("s_slider"), key="s_slider", help="Anzahl der Filialen (unten im Netz).")
        st.session_state[KEPT["s_slider"]] = s
        seed_widget("density_slider")
        density = st.slider("Netzdichte [%]", *bounds("density_slider"), key="density_slider", step=10, help="Anteil der möglichen Lanes (Werk → Verteilzentrum, Verteilzentrum → Filiale), die es gibt; Kosten je Lane 1 bis 9.")
        st.session_state[KEPT["density_slider"]] = density
        seed_widget("spread_slider")
        spread = st.slider("Streuung der Lane-Breiten [%]", *bounds("spread_slider"), key="spread_slider", step=25, help="0 = alle Lanes einer Stufe gleich breit, 100 = Kapazitäten gleichverteilt von 1 bis zum Doppelten der Grundbreite.")
        st.session_state[KEPT["spread_slider"]] = spread
        seed_widget("load_slider")
        load = st.slider("Auslastung [% der Werkskapazität]", *bounds("load_slider"), key="load_slider", step=10, help="Gesamtnachfrage der Filialen (alle Güter zusammen) in Prozent der Werkskapazität. Über 100 % kann das Netz die Nachfrage nicht mehr decken.")
        st.session_state[KEPT["load_slider"]] = load
        seed_widget("seed_input")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed. Die Verteilungen über 100 feste Netze weiter unten ändern sich dabei nicht - nur die Marke „Ihre Ziehung“.")
    else:
        K = int(st.session_state.get(KEPT["k_slider"], C.DEFAULT_K))
        p = int(st.session_state.get(KEPT["p_slider"], C.DEFAULT_P))
        d = int(st.session_state.get(KEPT["d_slider"], C.DEFAULT_D))
        s = int(st.session_state.get(KEPT["s_slider"], C.DEFAULT_S))
        density = int(st.session_state.get(KEPT["density_slider"], C.DEFAULT_DENSITY))
        spread = int(st.session_state.get(KEPT["spread_slider"], C.DEFAULT_SPREAD))
        load = int(st.session_state.get(KEPT["load_slider"], C.DEFAULT_LOAD))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen. Zahl der Güter, Werke, Verteilzentren und Filialen, Netzdichte, Streuung, Auslastung und Seed gehören zum zufälligen Netz.")

sync_query_params({"net_select": net_key, "k_slider": int(K), "order_radio": order, "p_slider": int(p), "d_slider": int(d), "s_slider": int(s),
                   "density_slider": int(density), "spread_slider": int(spread), "load_slider": int(load), "seed_input": int(seed)})

# feste Netze ignorieren die Zufallsregler: sonst würden gleiche Netze unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(p), int(d), int(s), int(density), int(spread), int(load), int(seed))
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)
    K = 0
with st.spinner("Rechne..."):
    a = _analysis(params, int(K), order)
mcf = a.mcf
level, code, dat = ev.verdict(a)
settings = (int(p), int(d), int(s), int(density), int(spread), int(load))
stages = a.stages
K = mcf.K
is_fixed = net_key in C.FIXED_NETS
lp_stage = next(i for i, s_ in enumerate(stages) if s_.kind == "lp")

# --- Stufen -------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Vom Einzelgut zum gemeinsamen Modell")
owner = (params, int(K), order)
if st.session_state.get("mcf_owner") != owner:
    st.session_state["mcf_stage"] = lp_stage
    st.session_state["mcf_owner"] = owner
step_col, play_col = st.columns([5, 2])
with step_col:
    stage_no = st.slider("Stufe", 0, len(stages) - 1, key="mcf_stage", help="0: jedes Gut allein; dann die Güter nacheinander in der gewählten Reihenfolge; dann das gemeinsame LP, das ganzzahlige Programm und die Entkopplung durch Schattenpreise.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch")
view_slot = st.empty()


def _caption(i):
    st_ = stages[i]
    if st_.kind == "single":
        return (f"Jedes Gut bekommt seinen billigsten Fluss, als wäre es allein im Netz: zusammen würden {_u(sum(st_.delivered))} Einheiten geliefert (das LP schafft {_u(dat['lp_delivered'])}) für {_u(st_.cost)}. "
                f"Dafür überschreitet die Summe der Güter auf {_edges(dat['n_over'])} die Kapazität (rote Unterlage, um insgesamt {_units(dat['over_total'])}) - diese Lösung ist **unzulässig**, aber eine untere Schranke.")
    if st_.kind == "seq":
        rest = f" Fertig: {_u(dat['seq_delivered'])} Einheiten für {_u(dat['seq_cost'])} - {_units(dat['seq_loss'])} weniger als das LP." if st_.step == K - 1 else ""
        return f"{mcf.names[a.order[st_.step]]} fährt auf der Restkapazität der vorigen Güter: bisher {_u(sum(st_.delivered))} Einheiten für {_u(st_.cost)}.{rest}"
    if st_.kind == "lp":
        text = (f"Gemeinsames LP: {_u(dat['lp_delivered'])} von {dat['demand']} Einheiten für {_u(dat['lp_cost'])}, {dat['n_vars']} Variablen, {dat['n_eq'] + dat['n_ub']} Nebenbedingungen, {dat['iterations']} Iterationen. "
                f"{_edges(dat['n_binding'])} {'ist' if dat['n_binding'] == 1 else 'sind'} bindend (orange) - an ihnen steht der Schattenpreis λ: der Wert einer zusätzlichen Einheit Kapazität (in der Belohnung M = {mcf.M} je gelieferter Einheit gemessen).")
        if dat["fractional"]:
            text += f" **Die Lösung ist gebrochen:** {dat['n_fractional']} Variablen sind nicht ganzzahlig (gestrichelt, größter Bruch {_f(dat['max_fraction'], 2)})."
        return text
    if st_.kind == "ilp":
        if dat["fractional"]:
            return f"Ganzzahlig (jede Einheit unteilbar): {_u(dat['ilp_delivered'])} statt {_u(dat['lp_delivered'])} Einheiten für {_u(dat['ilp_cost'])} - die Ganzzahligkeit kostet {_u(dat['deliv_gap'])} Einheiten Lieferung."
        return f"Ganzzahlig: {_u(dat['ilp_delivered'])} Einheiten für {_u(dat['ilp_cost'])} - genau das LP; die LP-Lösung war schon ganzzahlig, die Ganzzahligkeit kostet hier nichts."
    return (f"Mit den Schattenpreisen λ ist jedes Gut ein gewöhnlicher Min-Cost-Flow (SSP). Die {K} unabhängigen Flüsse ergeben mit −Σ λ·u den Wert {_f(dat['lagrange'], 1)} - der LP-Wert (Abweichung {_f(dat['lagrange_err'], 6)}). "
            + (f"Die Flüsse selbst sind aber nicht immer zulässig: auf {dat['dec_over']} gemeinsamen Kanten überschreiten sie die Kapazität (rot) - die Preise verraten den Wert, nicht die Lösung. Wie man aus den Einzelflüssen eine zulässige Lösung mischt, zeigt die Column Generation."
               if dat["dec_over"] else "Hier sind die Flüsse zufällig auch zulässig."))


def _render(i):
    with view_slot.container():
        c1, c2 = st.columns(2)
        st_ = stages[i]
        c1.markdown(f"**Stufe {i}:** {st_.title}")
        c2.markdown(f"**Lieferung und Kosten je Stufe** - {_u(sum(st_.delivered))} von {dat['demand']} Einheiten, Kosten {_u(st_.cost)}")
        duals = a.lp.duals if st_.kind in ("lp", "ilp") else None
        c1.plotly_chart(build_mcf(mcf, st_, duals), width="stretch", key=f"mcf_map_{i}")
        c2.plotly_chart(build_stages(stages, i, mcf.names, dat["demand"]), width="stretch", key=f"stage_chart_{i}")
        st.caption(_caption(i))


if auto_play:
    for i in range(len(stages)):
        _render(i)
        time.sleep(min(0.9, 8.0 / max(len(stages), 1)))
    stage_no = len(stages) - 1
else:
    _render(stage_no)

st.caption("Links: je Gut eine Farbe, die Güter einer Kante nebeneinander (Breite ~ Fluss); gestrichelt = gebrochener Fluss; rote Unterlage = die Summe der Güter überschreitet die gemeinsame Kapazität (Beschriftung Summe > Kapazität); orange Unterlage = bindende Kapazität mit Schattenpreis λ. "
           "Rechts oben die Lieferung je Stufe (gestapelt nach Gütern, gestrichelt die Nachfrage), unten die echten Kosten.")

st.markdown("---")

# --- Kernfrage ---------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Was kostet das Teilen?")
st.caption("**Lieferung** = gelieferte Einheiten aller Güter zusammen; **Kosten** = echte Kosten ohne die Belohnung; **nacheinander** = die Güter in der gewählten Reihenfolge; **Ganzzahligkeit** = was das ganzzahlige Programm gegen das LP verliert.")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Lieferung (LP)", f"{_u(dat['lp_delivered'])} von {dat['demand']}", delta=f"{_pct(dat['share'])} der Nachfrage", delta_color="off", help="Das gemeinsame LP liefert zuerst so viel wie möglich; jedes Gut allein würde " + f"{_u(dat['single_delivered'])} liefern - aber unzulässig.")
m2.metric("Kosten (LP)", _u(dat["lp_cost"]), delta=f"ganzzahlig {_u(dat['ilp_cost'])}", delta_color="off", help="Echte Kosten der LP-Lösung; im Delta die des ganzzahligen Programms.")
m3.metric("Nacheinander", f"{_u(dat['seq_delivered'])} geliefert", delta=f"{_units(dat['seq_loss'])} weniger als das LP" if dat["seq_loss"] > 1e-6 else "so viel wie das LP", delta_color="off", help=f"Reihenfolge: {' → '.join(mcf.names[k] for k in a.order)}; Kosten {_u(dat['seq_cost'])}. Beste Reihenfolge: {_u(dat['best_loss'])} weniger, schlechteste: {_u(dat['worst_loss'])} weniger.")
m4.metric("Größe", f"{dat['n_vars']} Variablen", delta=f"{dat['n_eq'] + dat['n_ub']} Nebenbedingungen, {dat['iterations']} Iterationen", delta_color="off", help="K·m Variablen: jedes Gut braucht eine Variable je Kante. Iterationen = Schritte des HiGHS-Lösers (nicht Sekunden).")

if code == "integral":
    st.success(f"✅ Das LP ist ganzzahlig: {_u(dat['lp_delivered'])} von {dat['demand']} Einheiten für {_u(dat['lp_cost'])}; die Ganzzahligkeit kostet hier nichts. "
               f"Zusammen ohne Rücksicht (jedes Gut allein) wären es {_u(dat['single_delivered'])} - dafür {'ist' if dat['n_over'] == 1 else 'sind'} {_edges(dat['n_over'])} überlastet. "
               + (f"Die Güter nacheinander liefern {_units(dat['seq_loss'])} weniger." if dat["seq_loss"] > 1e-6 else "Die Güter nacheinander erreichen hier zufällig dasselbe."))
elif code == "fractional":
    st.warning(f"⚠️ **Das LP ist gebrochen:** {dat['n_fractional']} Variablen sind nicht ganzzahlig (größter Bruch {_f(dat['max_fraction'], 2)}). Das LP liefert {_u(dat['lp_delivered'])} Einheiten für {_u(dat['lp_cost'])}, ganzzahlig gehen nur {_u(dat['ilp_delivered'])} für {_u(dat['ilp_cost'])} - "
               f"die Ganzzahligkeit kostet {_u(dat['deliv_gap'])} Einheiten Lieferung. Das ist genau die Lücke, die beim Ein-Gut-Fluss nie auftritt.")
else:
    st.warning("⚠️ Es kommt gar nichts an: kein Gut kann von einem Werk zu einer Filiale gelangen. Alle Lösungen liefern 0.")

if is_fixed:
    st.info("Festes Netz: es gibt nur diese eine Ziehung. Für die Verteilungen über viele Netze ein zufälliges Distributionsnetz wählen.")
    dist = None
else:
    dist = ev.distribution(int(K), *settings)
    st.markdown(f"**Nicht nur dieses eine Netz:** {len(C.DIST_SEEDS)} feste Netze mit denselben Einstellungen (Güter {K}, Werke {p}, Verteilzentren {d}, Filialen {s}, Netzdichte {density} %, Streuung {spread} %, Auslastung {load} %), getrennt vom Seed oben.")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("LP gebrochen", _share(dist["share_fractional"]), delta=f"ganzzahlig schlechter: {_share(dist['share_ilp_worse'])}", delta_color="off", help="Anteil der Netze, in denen das LP nicht ganzzahlig ist.")
    p2.metric("Nacheinander optimal", _share(dist["share_seq_optimal"]["given"]), delta=f"im Mittel {_f(sum(dist['seq_loss']['given']) / dist['n_seeds'], 1)} Einheiten weniger", delta_color="off", help="Anteil der Netze, in denen die Güter in der angegebenen Reihenfolge so viel liefern wie das LP (Kosten gleich oder kleiner).")
    p3.metric("Einzellösungen überlasten", _f(dist["over_mean"], 1) + " Kanten", delta=f"{_f(dist['single_overshoot_mean'], 1)} Einheiten zu viel", delta_color="off", help="Im Mittel überlasten die Einzellösungen so viele gemeinsame Kanten und wollen so viel mehr liefern, als das LP schafft.")
    p4.metric("Bindende Kanten", _f(dist["binding_mean"], 1), delta=f"{_f(dist['iterations_mean'], 0)} Iterationen", delta_color="off", help="Gemeinsame Kanten mit positivem Schattenpreis im LP, Mittel über die Netze; Iterationen des LP-Lösers.")
    st.plotly_chart(build_loss_hist(dist["seq_loss"], current=dat["seq_loss"] if order in HEUR_SHORT else None), width="stretch", key="loss_chart")
    st.caption(f"Über {len(C.DIST_SEEDS)} feste Netze fehlen bei den Güter nacheinander im Mittel {_f(sum(dist['seq_loss']['given']) / dist['n_seeds'], 1)} Einheiten gegen das LP (billigstes zuerst {_f(sum(dist['seq_loss']['cheap']) / dist['n_seeds'], 1)}, größte Nachfrage zuerst {_f(sum(dist['seq_loss']['large']) / dist['n_seeds'], 1)}); "
               f"die LP-Lösung ist in {_share(1 - dist['share_fractional'])} der Netze ganzzahlig.")

st.markdown("---")

# --- Vergleich -----------------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – die Lösungswege im Vergleich"):
    st.markdown("**Die Stufen für das Netz oben**")
    rows = [(f"{i}", s_.title, _u(sum(s_.delivered)), _u(s_.cost), str(len(s_.over)) if s_.kind in ("single", "decoupled") else "–") for i, s_ in enumerate(stages)]
    st.table({"Stufe": [r[0] for r in rows], "Verfahren": [r[1] for r in rows], "Lieferung": [r[2] for r in rows], "Kosten": [r[3] for r in rows], "überlastete Kanten": [r[4] for r in rows]})
    st.caption("Nur das gemeinsame LP und das ganzzahlige Programm sind zulässig und optimal (LP) bzw. optimal unter Ganzzahligkeit; die Einzellösungen sind eine untere Schranke und überlasten Kanten, die Güter nacheinander sind zulässig, aber nicht optimal, die Entkopplung liefert den richtigen Wert mit unzulässigen Flüssen.")
    st.markdown("**Alle Reihenfolgen der Güter nacheinander**")
    orders = sorted(a.seq_by_order.items(), key=lambda kv: (-kv[1].total_delivered, kv[1].cost, kv[0]))
    st.dataframe({"Reihenfolge": [" → ".join(mcf.names[k] for k in o) for o, _ in orders], "Lieferung": [_u(s_.total_delivered) for _, s_ in orders], "Kosten": [_u(s_.cost) for _, s_ in orders],
                  "fehlen gegen LP": [_u(a.lp.total_delivered - s_.total_delivered) for _, s_ in orders]}, hide_index=True, width="stretch")

st.markdown("---")

# --- Experimente -------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wann ist das LP gebrochen?")
st.caption("Beim Ein-Gut-Fluss ist jede Ecke ganzzahlig (totale Unimodularität). Mit mehreren Gütern nicht mehr: das LP darf gebrochene Ecken haben, und ganzzahlig lösen ist NP-schwer. Wie oft passiert das wirklich?")
if dist is None:
    st.info("Für die Verteilung über viele Netze ein zufälliges Distributionsnetz wählen. Das feste Netz „Frachtnetz mit Bruch“ zeigt einen gebrochenen Fall.")
else:
    st.markdown("**Distributionsnetz** (Ihre Einstellungen, 100 feste Netze):")
    st.table({"Zahl der Güter": [str(K)], "LP gebrochen": [_share(dist["share_fractional"])], "ganzzahlig schlechter": [_share(dist["share_ilp_worse"])], "Einzellösungen überlastet (Netze)": [_share(sum(1 for o in dist["cols"]["over"] if o > 0) / dist["n_seeds"])]})
if st.button("Frachtnetze mit Quelle-Ziel-Paaren durchrechnen (7 Familien × 100 Netze)", key="pairs_start"):
    st.session_state["pairs_on"] = True
if st.session_state.get("pairs_on"):
    pt = ev.pair_table()
    st.table({"Knoten": [str(r["family"][0]) for r in pt], "Kantendichte": [f"{r['family'][1]} %" for r in pt], "Güter": [str(r["family"][2]) for r in pt], "LP gebrochen (von 100)": [str(r["fractional"]) for r in pt],
              "ganzzahlig schlechter": [str(r["ilp_worse"]) for r in pt], "größte Lücke (Einheiten)": [_f(r["gap_max"], 1) for r in pt]})
    st.caption("Frachtnetze: zufällige gerichtete Graphen, Kapazität und Menge 1, jedes Gut fährt von seinem Start zu seinem Ziel - die Güter laufen gegeneinander, das ist die Situation, in der gebrochene Ecken entstehen können. "
               f"Trotzdem ist das LP fast immer ganzzahlig: {sum(r['fractional'] for r in pt)} von {sum(r['n'] for r in pt)} Netzen sind gebrochen. Die Lücke ist ein Worst-Case-Phänomen; das feste Netz „Frachtnetz mit Bruch“ ist so ein seltener Fall.")

st.subheader("🔬 Die Reihenfolge entscheidet")
st.caption("Güter nacheinander zu fahren ist billig und zulässig - jedes Gut ist ein Ein-Gut-Fluss auf der Restkapazität. Aber das Gut, das zuerst fährt, verbaut den anderen den Weg. Wie viel geht verloren, und hilft eine kluge Reihenfolge?")
if dist is None:
    st.info("Für die Verteilung über viele Netze ein zufälliges Distributionsnetz wählen. Für das feste Netz oben zeigt der Expander alle Reihenfolgen.")
else:
    n = dist["n_seeds"]
    rows = [(HEUR_SHORT[k], _share(dist["share_seq_optimal"][k]), _f(sum(dist["seq_loss"][k]) / n, 2), _f(sorted(dist["seq_loss"][k])[n // 2], 1), str(max(dist["seq_loss"][k]))) for k in ("given", "cheap", "large")]
    if "best_loss" in dist:
        rows += [("beste Reihenfolge (Aufzählung)", _share(dist["share_best_optimal"]), _f(sum(dist["best_loss"]) / n, 2), _f(sorted(dist["best_loss"])[n // 2], 1), str(max(dist["best_loss"]))),
                 ("schlechteste Reihenfolge (Aufzählung)", _share(1 - dist["share_worst_bad"]), _f(sum(dist["worst_loss"]) / n, 2), _f(sorted(dist["worst_loss"])[n // 2], 1), str(max(dist["worst_loss"])))]
    st.table({"Reihenfolge": [r[0] for r in rows], "so viel wie das LP": [r[1] for r in rows], "fehlende Lieferung (Mittel)": [r[2] for r in rows], "(Median)": [r[3] for r in rows], "(größter Wert)": [r[4] for r in rows]})
    st.caption(f"Über {n} feste Netze ({K} Güter). " + ("Auch die beste der Reihenfolgen erreicht das LP nur in " + _share(dist["share_best_optimal"]) + " der Netze; die schlechteste verliert im Mittel " + _f(sum(dist["worst_loss"]) / n, 1) + " Einheiten. " if "best_loss" in dist else "Bei fünf Gütern werden die 120 Reihenfolgen nicht aufgezählt. ")
               + "Eine Regel wie „billigstes zuerst“ hilft im Mittel, garantiert aber nichts - erst das gemeinsame Modell sieht alle Güter auf einmal.")

st.subheader("🔬 Preis des Teilens und Entkopplung durch Preise")
st.caption("Die Summe der Einzellösungen ist eine untere Schranke - unzulässig, weil Kanten überlastet sind. Die Schattenpreise des LP beziffern, was jede bindende Kante wert ist, und entkoppeln die Güter wieder: mit Preisen ist jedes Gut ein Ein-Gut-Fluss.")
if dist is None:
    st.info("Für die Verteilung über viele Netze ein zufälliges Distributionsnetz wählen. Für das feste Netz zeigen die Stufen 0 und die Entkopplung den Zusammenhang.")
else:
    q1, q2, q3 = st.columns(3)
    q1.metric("Einzellösungen wollen zu viel", _f(dist["single_overshoot_mean"], 1) + " Einheiten", delta=f"{_f(dist['over_mean'], 1)} überlastete Kanten", delta_color="off", help="Wie viel mehr die unabhängigen Einzellösungen liefern wollen, als das LP schafft (Mittel), und auf wie vielen gemeinsamen Kanten sie die Kapazität überschreiten.")
    q2.metric("Entkopplung trifft den LP-Wert", "exakt", delta=f"größte Abweichung {_f(dist['lagrange_err_max'], 6)}", delta_color="off", help="Mit den Schattenpreisen ergeben K unabhängige Min-Cost-Flows minus Σ λ·u genau den LP-Wert - in allen 100 Netzen.")
    q3.metric("Entkoppelte Flüsse überlastet", _share(dist["share_dec_over"]), help="Anteil der Netze, in denen die K unabhängigen Flüsse mit den Preisen gemeinsame Kanten überlasten: die Preise geben den Wert, aber nicht immer eine zulässige Lösung.")
    st.caption(f"Über {len(C.DIST_SEEDS)} feste Netze: die Preise entkoppeln die Güter und treffen den LP-Wert in jedem Netz exakt (Lagrange-Dualität), aber in {_share(dist['share_dec_over'])} der Netze überlasten die entkoppelten Flüsse mindestens eine Kante - "
               "mehrere Einzelflüsse zu einem zulässigen mischen ist die Idee der Column Generation (gebaut: mcf-column-generation-demo).")

st.subheader("🔬 Wie groß wird das LP?")
st.caption("K Güter auf m Kanten heißen K·m Variablen und K·(n − 2) Erhaltungsgleichungen dazu. Wie wachsen Größe und Iterationen des Lösers mit den Gütern und dem Netz?")
if dist is None:
    st.info("Für dieses Experiment ein zufälliges Distributionsnetz wählen.")
else:
    if st.button("Größen von 2 bis 5 Gütern und vier Netzgrößen durchrechnen (10 Netze je Zelle)", key="size_start"):
        st.session_state["size_on"] = True
    if st.session_state.get("size_on"):
        sz = ev.size_table()
        sl = ev.slopes(sz)
        st.plotly_chart(build_size(sz), width="stretch", key="size_chart")
        st.table({"Werke / DCs / Filialen": [f"{r['size'][0]} / {r['size'][1]} / {r['size'][2]}" for r in sz], "Güter": [str(r["K"]) for r in sz], "Kanten": [_f(r["m"], 0) for r in sz], "Variablen": [_f(r["vars"], 0) for r in sz],
                  "Nebenbedingungen": [_f(r["eq"] + r["ub"], 0) for r in sz], "Iterationen": [_f(r["nit"], 1) for r in sz]})
        st.caption(f"Mittel über 10 feste Netze je Zelle (Netzdichte 60 %, Streuung und Auslastung auf den Standardwerten). Die Variablen wachsen genau mit K·m; die Iterationen des Lösers wachsen schneller als die Größe (Steigung im doppelt logarithmischen Diagramm {_f(sl['nit'], 2)} gegen die Variablen). "
                   "Ab einigen Dutzend Gütern und Tausenden Kanten wird die Kanten-Formulierung unhandlich - dort setzen die Pfad-Formulierung mit Column Generation und Näherungsverfahren an.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist - und wer setzt an |
|---|---|
| **Eine Kapazität für die Summe der Güter** | Jede Einheit belegt gleich viel Kapazität; in der Praxis braucht Kühlware mehr Platz. **Ansatzpunkt:** Volumen je Gut in der Kapazitätszeile. |
| **Das Kanten-LP hat K·m Variablen** | Für viele Güter und große Netze wächst es unhandlich. **Ansatzpunkt: Pfad-Formulierung mit Column Generation** (gebaut: mcf-column-generation-demo): nur die Wege, die sich lohnen. |
| **Ein exaktes LP ist nötig** | Für sehr große Netze genügt oft ein guter Fluss mit garantierter Güte. **Ansatzpunkt: Garg–Könemann** (Näherung mit Preisen). |
| **Die Kanten stehen fest** | Hier gibt es die Lanes und Verteilzentren; wer sie erst bauen oder eröffnen muss, zahlt Fixkosten. **Ansatzpunkt:** Netzwerkdesign mit Fixkosten (Benders-Zerlegung, Slope Scaling). |
| **Teilbare Ströme** | Das LP darf halbe Einheiten schicken; ganzzahlig ist es NP-schwer. Die Lücke ist selten, aber real. **Ansatzpunkt:** ganzzahliges Programm, Branch and Cut. |
| **Keine Zeit** | Ein Fluss ist eine Momentaufnahme. **Ansatzpunkt:** Zeit-Raum-Netz in der Demo „leercontainer-demo“. |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: Edmonds-Karp, Dinic, Push-Relabel, Successive Shortest Paths, Cycle-Canceling, Cost Scaling, Mehrgüterfluss (dieses Stück), Column Generation (gebaut), Garg-Könemann, Fixkosten-Netzwerkdesign, Benders-Zerlegung und Slope Scaling - bisher sind die ersten acht gebaut.")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell (Kanten-Formulierung).** Gerichteter Graph $G=(V,E)$, $K$ Güter, gemeinsame Kapazitäten $u_e$ auf $E_J\subseteq E$, gutspezifische Obergrenzen $b_{k,e}$, Kosten $c_{k,e}$; Belohnung $M$ je Einheit auf den Kanten $E_T$ in die Senke $t$:
$$\min\ \sum_{k}\sum_{e}c_{k,e}x_{k,e}-M\sum_k\sum_{e\in E_T}x_{k,e}$$
$$\text{u.d.N.}\quad \sum_{e\in\delta^-(v)}x_{k,e}-\sum_{e\in\delta^+(v)}x_{k,e}=0\ \ (\forall k,\ \forall v\ne s,t),\qquad \sum_k x_{k,e}\le u_e\ \ (e\in E_J),\qquad 0\le x_{k,e}\le b_{k,e}.$$
Mit hinreichend großem $M$ liefert das LP zuerst die größte Lieferung und darunter die kleinsten Kosten.

**Dual.** Zu den gemeinsamen Kapazitäten gehören Schattenpreise $\lambda_e\ge 0$ (komplementärer Schlupf: $\lambda_e>0\Rightarrow\sum_k x_{k,e}=u_e$).

**Lagrange-Entkopplung.** Relaxiert man $\sum_k x_{k,e}\le u_e$ mit $\lambda$, zerfällt das Problem in $K$ unabhängige Min-Cost-Flows mit Kosten $c_{k,e}+\lambda_e$:
$$L(\lambda)=\sum_k\min_{x_k\in P_k}\ \sum_e (c_{k,e}+\lambda_e)x_{k,e}\ -\ \sum_{e\in E_J}\lambda_e u_e,$$
und es gilt $\max_{\lambda\ge0}L(\lambda)=$ LP-Optimum (starke Dualität). Die Minimierer für ein optimales $\lambda$ sind im Allgemeinen nicht zulässig für die gemeinsame Kapazität - erst eine Mischung (Column Generation) ist es.

**Ganzzahligkeit.** Die Nebenbedingungsmatrix ist nicht total unimodular (ein Gut: ja, mehrere: nein). Das LP kann gebrochene Ecken haben (Beispiel: zwei Güter, LP-Wert 1,5, ganzzahlig 1); ganzzahliger Mehrgüterfluss ist NP-schwer (Even, Itai, Shamir 1976). Ohne Rücksicht auf die Ganzzahligkeit ist das LP in polynomieller Zeit lösbar, aber mit $K\cdot m$ Variablen.

**Nacheinander.** Jedes Gut ist ein Ein-Gut-Fluss auf der Restkapazität $u_e-\sum_{j<k}x_{j,e}$ (SSP): zulässig, aber der Wert hängt von der Reihenfolge ab und ist im Allgemeinen nicht optimal.

Implementiert in `mcf_scenario.py` (Netz, eigener Zufallsgenerator), `mcf_model.py` (Güter, Grenzen, Frachtnetze), `mcf_solve.py` (LP und ILP mit HiGHS über `scipy`, Einzelgut-Verfahren über SSP, Entkopplung), `mcf_ssp.py` (Kopie der SSP-Demo), `mcf_evaluation.py` (Stufen, Kennzahlen, Verteilungen, Experimente).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
