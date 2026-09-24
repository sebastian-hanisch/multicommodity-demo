# Mehrgüterfluss – Güter teilen sich die Kanten – Streamlit-Demo

*(noch nicht deployed)*

Siebtes Stück der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", Beginn des Mehrgüter-Asts:
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Modell – das **Kanten-LP des Mehrgüterflusses** – an einem wachsenden Beispiel.
In den ersten sechs Stücken war alles **ein Gut**: ein Fluss, ein Preis je Einheit, und [Successive Shortest Paths](https://github.com/sebastian-hanisch/ssp-demo) fand den billigsten Fluss. Jetzt fahren **mehrere Güter** (Frische, Trocken, Kühl, Getränke, Tiefkühl) über dieselben Lanes und Verteilzentren; die Kapazität gilt für die **Summe**.
Die Demo führt von *jedes Gut allein* (zusammen zu viel, unzulässig) über *nacheinander* (zulässig, aber die Reihenfolge entscheidet) zum **gemeinsamen LP** (eine Variable je Gut und Kante, optimal, mit **Schattenpreisen** der gemeinsamen Kapazitäten), zum ganzzahligen Programm und zur **Entkopplung**: mit den Schattenpreisen ist jedes Gut wieder ein gewöhnlicher Min-Cost-Flow.
Vehikel wie in den Vorgänger-Demos: ein Distributionsnetz (Werke → Verteilzentren → Filialen) mit Kosten je Einheit, dazu zwei feste Frachtnetze (Quelle-Ziel-Paare mit Kapazität 1).

**Einordnung in die Reihe (die Kanten des Graphen):** Der Ein-Gut-Fluss ist der Sonderfall K = 1 (Test: gleich dem Optimum von `networkx`). Mit mehreren Gütern geht die **totale Unimodularität** verloren: das LP *kann* gebrochene Ecken haben, ganzzahliger Mehrgüterfluss ist NP-schwer, und die Ein-Gut-Verfahren der ersten Stücke lassen sich nicht mehr nacheinander einsetzen.
Das öffnet die Folgestücke: die **Pfad-Formulierung mit Column Generation** (gegen die Größe des Kanten-LP; die Entkopplung durch Preise ist ihre Idee), **Garg–Könemann** (Näherung mit Preisen) und das **Netzwerkdesign mit Fixkosten** (Benders-Zerlegung, Slope Scaling).
Bisher gebaut: die ersten zehn Stücke.
```
edmonds-karp-demo (Wurzel: Restgraph, Rückkanten, Max-Flow = Min-Cut)                  [gebaut]
  ├─ dinic-demo (viele kürzeste Wege je Phase: Niveaugraph, blockierender Fluss)        [gebaut]
  ├─ push-relabel-demo (kein Weg: Überschüsse schieben, Höhen anheben)                 [gebaut]
  └─ ssp-demo (Kosten: der billigste Weg im Restgraphen, Potenziale)                    [gebaut]
       ├─ cycle-canceling-demo (negative Kreise löschen) → Netzwerksimplex               [gebaut]
       │    (network-flow-demo)                                                          [gebaut als Fall-Demo]
       ├─ cost-scaling-demo (Push-Relabel + ε-Skalierung, das nutzt OR-Tools)           [gebaut]
       └─ multicommodity-demo (mehrere Güter teilen Kapazität: Kanten-LP, Preise)       [dieses Stück]
            ├─ mcf-column-generation-demo (Pfade als Spalten, Pricing = Dijkstra)       [gebaut]
            ├─ garg-koenemann-demo (Näherung mit Preisen, ohne LP-Löser)                [gebaut]
            └─ fixkosten-netzdesign-demo (Fixkosten: Schranke und Schnitte)             [gebaut]
                 ├─ Benders-Zerlegung (Entwurf im Master, Fluss im Teilproblem)         [geplant]
                 └─ Slope Scaling (Heuristik für große Netze)                           [geplant]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: die Lehrnetze von Hand, das Beispielnetz über seinen Seed, die Verteilungen über 100 feste Netze (Seeds 100000–100099, dieselben wie in den Vorgänger-Demos). Standard: 3 Güter, 3 Werke, 3 Verteilzentren, 8 Filialen, Netzdichte 60 %, Streuung 50 %, Auslastung 90 %. Jedes Werk stellt ein Gut mit 70 % Wahrscheinlichkeit her, die Nachfrage der Filialen wird zufällig auf die Güter verteilt; Kostenfaktor auf den Lanes 2 / 1 / 3 / 1 / 4 (Frische, Trocken, Kühl, Getränke, Tiefkühl).
Belohnung M = 1000 je gelieferter Einheit: das LP liefert zuerst so viel wie möglich, darunter so billig wie möglich. Die SSP-Kopie ist gegen die Vorgänger-Demo bewacht: 53 907 durchsuchte Kanten über die 100 Netze, Kosten gleich dem Optimum von `networkx`.

| Frage | Ergebnis |
|---|---|
| Stimmt das LP? | ✅ Für K = 1 gleich größter und billigster Fluss von `networkx`; ganzzahlig gegen Brute-Force-Aufzählung auf den kleinen Frachtnetzen; Innere-Punkte-Verfahren = Simplex; Zulässigkeit je Lösung (Erhaltung je Gut, gemeinsame Kapazität, Obergrenzen); Schattenpreise ≥ 0 mit komplementärem Schlupf; starke Dualität. |
| Wird das LP oft gebrochen? | ❌ Nein, das war die Vorab-Vermutung: **0 von 100 Netzen** für 2, 3, 4 und 5 Güter, das ganzzahlige Programm ist nie schlechter. |
| Und wenn die Güter gegeneinander laufen? | ⚠️ Frachtnetze (Kapazität und Menge 1, jedes Gut von seinem Start zu seinem Ziel): in 6 von 7 Familien 0 gebrochene LPs von 100, in (8 Knoten, 30 %, 5 Güter) **1**, mit Lücke 0,5 Einheiten; in der Familie (5 Knoten, 55 %, 2 Güter) 4 von 1500. Die Lücke ist ein Worst-Case-Phänomen, das Lehrnetz „Frachtnetz mit Bruch“ ist so ein Fall: LP 1,5 Einheiten für 24, ganzzahlig 1 für 15 (9 gebrochene Variablen, größter Bruch 0,5). |
| Was kostet das Teilen? | Jedes Gut allein würde im Mittel **5,5 Einheiten mehr** liefern, als das LP schafft (75,8 Nachfrage, 64,3 geliefert), auf im Mittel **3,9 gemeinsamen Kanten** überlastet, in **97 von 100 Netzen** mindestens eine; im LP sind im Mittel 3,4 Kanten bindend. |
| Reicht „nacheinander“? | ❌ Zulässig, aber nicht optimal: drei Güter so viel wie das LP in **5 %** (angegebene Reihenfolge), 9 % (billigstes zuerst), 7 % (größte Nachfrage zuerst); im Mittel fehlen 4,97 / 3,98 / 5,12 Einheiten. Die beste der 6 Reihenfolgen erreicht das LP in 18 %, die schlechteste ist in 97 % schlechter (im Mittel fehlen 1,21 bzw. 8,18, größter Wert 11 bzw. 24). |
| Und mit mehr Gütern? | Angegebene Reihenfolge, Anteil so gut wie das LP: 16 / 5 / 3 / 6 % für 2 / 3 / 4 / 5 Güter; im Mittel fehlen 4,86 / 4,97 / 5,39 / 4,82 Einheiten; beste Reihenfolge erreicht das LP in 33 / 18 / 16 % (2 / 3 / 4 Güter; bei 5 werden die 120 Reihenfolgen nicht aufgezählt). |
| Entkoppeln die Preise die Güter? | ✅ Wert exakt: K unabhängige Min-Cost-Flows mit Kosten c + λ, minus Σ λ·u, ergeben in allen 100 Netzen den LP-Wert (Abweichung < 10⁻⁶; über SSP unabhängig nachgerechnet); für beliebige Preise ist der Wert eine untere Schranke. ❌ Die Flüsse selbst sind aber in **69 von 100 Netzen** nicht zulässig (2 / 3 / 4 / 5 Güter: 62 / 69 / 71 / 72 %) – die Preise verraten den Wert, nicht die Lösung. Daraus mischt die Column Generation eine zulässige. |
| Wie groß wird das LP? | 2 / 3 / 4 / 5 Güter: **69 / 103 / 137 / 172 Variablen** (K·m), 18,3 / 23,0 / 26,5 / 30,4 Iterationen des Lösers im Mittel; die Iterationen wachsen mit Steigung **1,47** gegen die Variablen im doppelt logarithmischen Diagramm – schneller als die Größe. |
| Beispielnetz (Seed 155) | 67 von 76 Einheiten für 1548, 114 Variablen, 40 Iterationen; ganzzahlig gleich; jedes Gut allein 76 Einheiten, dafür 6 gemeinsame Kanten überlastet (5 bindend); nacheinander 67 für 1610 (in Kosten schlechter, in der Menge gleich); schlechteste Reihenfolge (Trocken, Kühl, Frische) nur 51. Fünf Güter: LP 76 von 76 für 2234, nacheinander 66 (beste Reihenfolge fehlen 5, schlechteste 23). |
| Reihenfolge-Falle | Lehrnetz: LP 4 von 5 Einheiten; von den 6 Reihenfolgen liefern drei 4, drei nur 3 – die beste Reihenfolge verliert nichts, die schlechteste 1. |

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Schreiben der Texte wurde über die 100 Netze gemessen; einige Vermutungen aus dem Plan stimmten nicht oder nur teilweise:

- **„Das LP wird oft gebrochen.“** Falsch: in keinem der 400 Distributionsnetze (100 je 2 bis 5 Güter). Die Lücke braucht Güter, die gegeneinander laufen – und selbst in Frachtnetzen ist sie mit 1 von 700 (bzw. 4 von 1500 in der günstigsten Familie) selten. Deshalb zeigt die Demo den gebrochenen Fall an einem festen Lehrnetz statt ihn zufällig zu erwarten.
- **„Nacheinander mit klugem Startgut ist fast optimal.“** Nur die Aufzählung aller Reihenfolgen hilft, und auch die erreicht das LP nur in 18 % der Netze (3 Güter); billigstes zuerst hilft im Mittel etwas (3,98 gegen 4,97 fehlende Einheiten), größte Nachfrage zuerst nicht (5,12), und keine Regel garantiert etwas.
- **„Die Entkopplung durch Preise liefert die Lösung.“** Sie liefert den **Wert** exakt, aber die Einzelflüsse überlasten in 69 % der Netze Kanten. Das ist der ehrliche Übergang zur Column Generation, nicht ein Fehler der Demo.
- **„Die Größe ist harmlos, weil das LP ja polynomiell ist.“** Die Variablen wachsen genau mit K·m, die Iterationen schneller (Steigung 1,47) – gemessen in Löser-Iterationen, nicht in Sekunden.
- **Abweichungen vom Plan:** Port 8680; kein PDF-Export; die Belohnung M ersetzt die geplanten Schlupfvariablen mit Strafe (gleiche Wirkung, lexikographisch: erst liefern, dann sparen); die Negativkontrolle „Einzelflüsse ohne Prüfung zusammenlegen“ steckt in der Stufe 0 (Anteil überlasteter Netze) statt in einem eigenen Experiment; die Experimente 3 und 4 des Plans (Preis des Teilens, Entkopplung) sind Kennzahlen in der Kernfrage statt Buttons.

## Was die Demo zeigt

- **Stufenregler:** Stufe 0 = jedes Gut allein (rote Unterlage, wo die Summe die Kapazität überschreitet, Beschriftung Summe > Kapazität), dann die Güter nacheinander in der gewählten Reihenfolge (angegeben / billigstes / größte Nachfrage / beste / schlechteste per Aufzählung), dann das **gemeinsame LP** (orange Unterlage und λ an den bindenden Kanten, gestrichelt = gebrochener Fluss), das **ganzzahlige Programm** und die **Entkopplung** durch Schattenpreise. Links das Netz (je Gut eine Farbe, Breite ~ Fluss, die Güter einer Kante nebeneinander), rechts Lieferung je Stufe (gestapelt nach Gütern, gestrichelt die Nachfrage) und Kosten. ▶️ spielt alle Stufen ab.
- **Was kostet das Teilen?** Lieferung, Kosten, Nacheinander, Größe; darunter ein Urteil (LP ganzzahlig / gebrochen / nichts kommt an) und die Verteilung über 100 feste Netze (Histogramm der fehlenden Lieferung nacheinander mit der Marke „Ihre Ziehung“).
- **Experimente (🔬):** Wann ist das LP gebrochen (Frachtnetze: 7 Familien × 100 Netze, auf Abruf), die Reihenfolge entscheidet (Tabelle über die Reihenfolgen), Preis des Teilens und Entkopplung durch Preise, Größe von 2 bis 5 Gütern und vier Netzgrößen (auf Abruf).
- **Feste Netze:** „Frachtnetz mit Bruch“ (das LP liefert 1,5, ganzzahlig 1) und „Reihenfolge-Falle“ (die Reihenfolge entscheidet 4 gegen 3); dazu zufällige Distributionsnetze mit 2 bis 5 Gütern. **Wo die Annahmen enden:** Volumen je Gut, Größe, Näherung, Fixkosten, Ganzzahligkeit, Zeit.

## Modell und Verfahren

- **Netz:** wie in der SSP-Demo (Quelle S, Werke, Verteilzentren als Eingang und Ausgang gespalten, Filialen, Senke T), Kosten je Einheit. Ganzzahlig, eigener Zufallsgenerator SplitMix64 statt `numpy.random`.
- **Kanten-LP:** Variablen x[k][e] ≥ 0; Flusserhaltung je Gut und Knoten; **gemeinsame Kapazität** Σₖ x[k][e] ≤ u[e] auf Werks-, Lane- und Verteilzentrumkanten; gutspezifische Obergrenzen (ein Werk stellt nicht jedes Gut her, die Nachfragekante trägt höchstens die Filialnachfrage des Guts). Ziel: Σ Kosten·x − M · Lieferung.
- **Schattenpreise:** die Duallösung der gemeinsamen Kapazitäten (HiGHS, `scipy.optimize.linprog`); bindend = positiver Preis auf einer ausgelasteten Kante. Das ganzzahlige Programm mit `scipy.optimize.milp`.
- **Einzelgut, nacheinander, Entkopplung:** jedes Gut ist ein gewöhnlicher Min-Cost-Flow (SSP-Kopie); nacheinander auf der Restkapazität, Entkopplung mit Kosten c + λ.
- **Aufwand:** Variablen, Nebenbedingungen und **Iterationen des Lösers**, nie Sekunden.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `mcf_constants.py` | Regler-Grenzen, Presets und Hilfetexte, feste Seed-Mengen |
| `mcf_presets.py` | Permalink, Preset- und Zufalls-Seed-Logik (Standardmuster des Portfolios) |
| `mcf_scenario.py` | Distributionsnetz mit Kosten, eigener Zufallsgenerator |
| `mcf_model.py` | Güter, gutspezifische Grenzen, Kostenfaktoren, Frachtnetze mit Quelle-Ziel-Paaren, Lehrnetze (Bruch, Reihenfolge) |
| `mcf_solve.py` | LP und ganzzahliges Programm (HiGHS), jedes Gut allein, nacheinander, Entkopplung durch Preise |
| `mcf_ssp.py`, `mcf_edmonds_karp.py` | Kopien der Vorgänger-Demos (Min-Cost-Flow je Gut), ohne Import, SSP durch einen Wache-Test bewacht |
| `mcf_evaluation.py` | Stufen, Urteil, Reihenfolgen, Verteilungen, Frachtnetz-Tabelle, Größentabelle |
| `mcf_visualization.py` | Plotly-Abbildungen (Achsen gesperrt für Touch-Geräte; Kantenbeschriftungen als Annotationen mit heller Hinterlegung; Hover über unsichtbare Marker entlang der Kanten) |
| `tests/` | Algorithmus (K = 1 gegen `networkx`, Brute Force, Simplex gegen Innere Punkte, Dualität, Entkopplung), Szenario und Auswertung, Presets, belegte Zahlen, AppTest-Rauchtests |

Alle Daten sind synthetisch; die Laufzeit braucht numpy, pandas, plotly, streamlit und **scipy** (der LP-Löser HiGHS), `networkx` ist ein reines Testorakel.

## Lokal starten

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

## Tests ausführen

```bash
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -v
```

Kosten und Mengen sind ganzzahlig; die Zielwerte des LP werden mit Toleranz verglichen (nicht die Basis des Simplex), und die im Text genannten Anteile und Mittel stehen auf 100 festen Netzen. Die CI (`.github/workflows/tests.yml`) läuft auf Ubuntu mit Python 3.12, bei jedem Push und wöchentlich mit den jeweils neuesten Bibliotheksversionen.
