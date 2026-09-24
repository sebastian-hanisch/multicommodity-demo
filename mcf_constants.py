"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Mehrgüterfluss: Güter teilen sich die Kanten"."""

# --- Regler (wie in den Vorgänger-Demos) ----------------------------------------------------------------------------------------
P_MIN, P_MAX, DEFAULT_P = 2, 6, 3            # Werke
D_MIN, D_MAX, DEFAULT_D = 2, 6, 3            # Verteilzentren
S_MIN, S_MAX, DEFAULT_S = 3, 12, 8           # Filialen
DENSITY_MIN, DENSITY_MAX, DEFAULT_DENSITY = 20, 100, 60   # Anteil vorhandener Lanes in ganzen Prozent, Schritt 10
SPREAD_MIN, SPREAD_MAX, DEFAULT_SPREAD = 0, 100, 50       # Streuung der Lane-Breiten in ganzen Prozent, Schritt 25
LOAD_MIN, LOAD_MAX, DEFAULT_LOAD = 40, 160, 90            # Gesamtnachfrage in Prozent der Werkskapazität, Schritt 10
DEFAULT_SEED = 155
SEED_MAX = 2_000_000_000

NETS = {
    "random": "Distributionsnetz mit mehreren Gütern",
    "gap": "Frachtnetz mit Bruch (2 Güter, LP gebrochen)",
    "order": "Frachtnetz: die Reihenfolge entscheidet (3 Güter)",
}
DEFAULT_NET = "random"
FIXED_NETS = ("gap", "order")

K_MIN, K_MAX, DEFAULT_K = 2, 5, 3            # Zahl der Güter
ORDER_LABELS = {"given": "Wie angegeben (Frische, Trocken, ...)", "cheap": "Billigstes Gut zuerst", "large": "Größte Nachfrage zuerst", "best": "Beste Reihenfolge (Aufzählung)", "worst": "Schlechteste Reihenfolge (Aufzählung)"}
DEFAULT_ORDER = "given"

# --- feste Seed-Mengen (dieselben wie in der Edmonds-Karp-Demo; unabhängig vom Nutzer-Seed) -----------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
SCALE_SIZES = ((2, 2, 4), (3, 3, 8), (4, 4, 16), (6, 6, 12))   # (Werke, DCs, Filialen)
SCALE_SEEDS = DIST_SEEDS[:10]
K_SWEEP = (2, 3, 4, 5)
PAIR_FAMILIES = ((5, 55, 2), (5, 55, 3), (5, 55, 4), (6, 45, 3), (6, 45, 5), (8, 30, 3), (8, 30, 5))   # (Knoten, Kantendichte %, Güter): Kapazität und Menge 1

COLORS = {
    "flow": "#1f77b4", "path": "#2ca02c", "back": "#ff7f0e", "cut": "#d62728", "reach": "#2ca02c", "dead": "#9467bd",
    "unreach": "#8c8c8c", "faint": "rgba(150,150,150,0.45)", "node": "#111111", "optimal": "#d62728", "levels": "Viridis",
}

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net="random", k=DEFAULT_K, order=DEFAULT_ORDER, p=DEFAULT_P, d=DEFAULT_D, s=DEFAULT_S, density=DEFAULT_DENSITY, spread=DEFAULT_SPREAD, load=DEFAULT_LOAD, seed=DEFAULT_SEED)
PRESETS = {
    "🚚 Zufallsnetz": {**_BASE},
    "🧊 Fünf Güter": {**_BASE, "k": 5},
    "📉 Schlechteste Reihenfolge": {**_BASE, "order": "worst"},
    "🏆 Beste Reihenfolge": {**_BASE, "order": "best", "seed": 101},
    "🏭 Werke knapp": {**_BASE, "load": 140},
    "🕸️ Dünnes Netz": {**_BASE, "density": 30},
    "🧩 Frachtnetz mit Bruch": {**_BASE, "net": "gap", "k": 2},
    "🧭 Reihenfolge-Falle": {**_BASE, "net": "order", "order": "worst"},
}
PRESET_HELP = {
    "🚚 Zufallsnetz": "Das Netz der Vorgänger-Demos (Seed 155) mit drei Gütern: das gemeinsame LP liefert 67 von 76 Einheiten für 1548; jedes Gut allein würde alle 76 liefern, überlastet dabei aber 6 gemeinsame Kanten. 114 Variablen, 40 Iterationen.",
    "🧊 Fünf Güter": "Fünf statt drei Güter: das LP liefert alle 76 Einheiten (2234), die Güter nacheinander in angegebener Reihenfolge nur 66 - 10 Einheiten fehlen; auch die beste Reihenfolge verliert noch 5.",
    "📉 Schlechteste Reihenfolge": "Dasselbe Netz, aber die schlechteste der 6 Reihenfolgen (Trocken, Kühl, Frische): nur 51 statt 67 Einheiten - 16 fehlen. Das Gut, das zuerst fährt, verbaut den anderen den Weg.",
    "🏆 Beste Reihenfolge": "Seed 101: in der angegebenen Reihenfolge fehlen 6 Einheiten, in der besten Reihenfolge fehlt keine; die schlechteste verliert 13 von 77. Die beste Reihenfolge kennt man aber erst, wenn man alle durchprobiert - oder das LP löst.",
    "🏭 Werke knapp": "Nachfrage 140 % der Werkskapazität: das LP liefert 67 von 118; die Einzellösungen wollten 105 liefern und überlasten dafür 9 gemeinsame Kanten.",
    "🕸️ Dünnes Netz": "Nur 30 % der möglichen Lanes: das LP liefert 45 von 76 Einheiten, die Einzellösungen 54.",
    "🧩 Frachtnetz mit Bruch": "Fünf Knoten, zwei Güter, alle Kapazitäten und Mengen 1: das LP liefert 1,5 Einheiten (jedes Gut halb über zwei Wege, gestrichelt), ganzzahlig gehen nur 1,0 - die LP-Lösung ist gebrochen. Solche Fälle sind selten: in dieser Familie (5 Knoten, 2 Güter, Kapazität und Menge 1) 4 von 1500 Zufallsinstanzen.",
    "🧭 Reihenfolge-Falle": "Sechs Knoten, drei Güter: das LP liefert 4 von 5 Einheiten; von den sechs Reihenfolgen erreichen drei das Optimum, drei nur 3 Einheiten. Das Gut, das zuerst fährt, verbaut den anderen den Weg.",
}
