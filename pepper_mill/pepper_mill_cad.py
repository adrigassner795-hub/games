"""
Pfeffermuehle - parametrisches CAD-Modell (2 Teile: Kopf + Body)

Erzeugt STEP-Dateien, die sich direkt in SolidWorks oeffnen lassen
(File > Open > *.step  ->  wird als Volumenkoerper / "Solid Body" importiert).

Alle Masse in Millimetern, abgeleitet aus der Handskizze.
Masse, die in der Skizze nicht eindeutig lesbar waren, sind unten mit
"# Annahme" markiert - einfach den Wert anpassen und Skript neu ausfuehren.

Ausfuehren:  python3 pepper_mill_cad.py
"""

import math
import os

import cadquery as cq

OUT = os.path.dirname(os.path.abspath(__file__))

# ===================================================================
#  MASSE  (bei Bedarf hier anpassen)
# ===================================================================

# ---- KOPF (oberes Teil) --------------------------------------------
H_OUTER_D       = 40.0    # Aussendurchmesser Kopf            (Skizze Phi40)
H_TOTAL_H       = 22.0    # Gesamthoehe Kopf                  (Skizze 22)
H_SPIGOT_D      = 29.7    # Zentrierzapfen unten              (Skizze Phi29,7)
H_SPIGOT_H      = 3.0     # Hoehe Zentrierzapfen              (Skizze 3)
H_TOP_CBORE_D   = 10.0    # Senkung oben                      (Skizze Phi10)
H_TOP_CBORE_H   = 4.0     # Tiefe Senkung oben                (Skizze 4)
H_CENTER_HOLE_D = 6.0     # zentrale Bohrung (Antriebswelle)  (Skizze Phi6)
H_BOT_RECESS_D  = 20.0    # Aussparung unten im Zapfen        (Skizze Phi20)
H_BOT_RECESS_H  = 5.0     # Tiefe der Aussparung unten        # Annahme
H_M3_BC         = 12.5    # Lochkreis-Durchmesser M3-Schrauben(Skizze 12,5)
H_M3_DRILL_D    = 2.5     # Kernlochbohrung fuer M3-Gewinde
H_M3_DEPTH      = 8.0     # Bohrtiefe -> M3x8
H_M3_COUNT      = 2       # Anzahl Schraubloecher             # Annahme

# ---- BODY (unteres Teil) -------------------------------------------
B_OUTER_D       = 40.0    # Aussendurchmesser Body            (Skizze Phi40)
B_TOTAL_H       = 85.0    # Gesamthoehe Body                  (Skizze 85)
B_TOP_BORE_D    = 30.0    # obere Aufnahme fuer Kopf-Zapfen   (Skizze Phi30)
B_TOP_BORE_H    = 12.0    # Tiefe obere Aufnahme              (Skizze 12)
B_MAIN_BORE_D   = 24.0    # durchgehende Innenbohrung         (Skizze Phi24)
B_BOT_BORE_D    = 36.0    # untere Aufnahme fuer Mahlwerk     (Skizze Phi36)
B_BOT_BORE_H    = 12.0    # Tiefe untere Aufnahme             (Skizze 12)
B_M3_BC         = 28.5    # Lochkreis-Durchmesser M3-Schrauben(Skizze 28,5)
B_M3_DRILL_D    = 2.5     # Kernlochbohrung fuer M3-Gewinde
B_M3_DEPTH      = 8.0     # Bohrtiefe -> M3x8
B_M3_COUNT      = 2       # Anzahl Schraubloecher

CHAMFER = 0.7             # kleine Fasen an Aussenkanten / Einfuehrkante


# ===================================================================
#  GEOMETRIE
# ===================================================================

def _bolt_circle(count, bc_diameter):
    """Liefert (x, y)-Positionen auf einem Lochkreis (erstes Loch bei 90 Grad)."""
    r = bc_diameter / 2.0
    return [
        (r * math.cos(math.radians(90 + i * 360.0 / count)),
         r * math.sin(math.radians(90 + i * 360.0 / count)))
        for i in range(count)
    ]


def make_head():
    """Kopf: Z=0 unten am Zentrierzapfen, Z=H_TOTAL_H oben."""
    # Zentrierzapfen unten (mit Einfuehrfase)
    spigot = cq.Workplane("XY").circle(H_SPIGOT_D / 2).extrude(H_SPIGOT_H)
    spigot = spigot.edges("<Z").chamfer(CHAMFER)

    # Hauptkoerper / Kappe
    cap = (cq.Workplane("XY")
           .circle(H_OUTER_D / 2)
           .extrude(H_TOTAL_H - H_SPIGOT_H)
           .translate((0, 0, H_SPIGOT_H)))

    head = spigot.union(cap)
    head = head.edges(">Z").chamfer(CHAMFER)

    # zentrale Bohrung Phi6 (von Aussparung unten bis Oberkante)
    center = (cq.Workplane("XY")
              .circle(H_CENTER_HOLE_D / 2)
              .extrude(H_TOTAL_H - H_BOT_RECESS_H)
              .translate((0, 0, H_BOT_RECESS_H)))
    head = head.cut(center)

    # Senkung oben Phi10
    cbore = (cq.Workplane("XY")
             .circle(H_TOP_CBORE_D / 2)
             .extrude(H_TOP_CBORE_H)
             .translate((0, 0, H_TOTAL_H - H_TOP_CBORE_H)))
    head = head.cut(cbore)

    # Aussparung unten Phi20
    recess = cq.Workplane("XY").circle(H_BOT_RECESS_D / 2).extrude(H_BOT_RECESS_H)
    head = head.cut(recess)

    # M3-Gewindebohrungen (Kernloch) auf dem Boden der Aussparung
    for x, y in _bolt_circle(H_M3_COUNT, H_M3_BC):
        hole = (cq.Workplane("XY")
                .circle(H_M3_DRILL_D / 2)
                .extrude(H_M3_DEPTH)
                .translate((x, y, H_BOT_RECESS_H)))
        head = head.cut(hole)

    return head


def make_body():
    """Body: Z=0 unten, Z=B_TOTAL_H oben."""
    body = cq.Workplane("XY").circle(B_OUTER_D / 2).extrude(B_TOTAL_H)
    body = body.edges("<Z or >Z").chamfer(CHAMFER)

    # durchgehende Innenbohrung Phi24
    main = cq.Workplane("XY").circle(B_MAIN_BORE_D / 2).extrude(B_TOTAL_H)
    body = body.cut(main)

    # obere Aufnahme Phi30 (nimmt den Kopf-Zentrierzapfen auf)
    top = (cq.Workplane("XY")
           .circle(B_TOP_BORE_D / 2)
           .extrude(B_TOP_BORE_H)
           .translate((0, 0, B_TOTAL_H - B_TOP_BORE_H)))
    body = body.cut(top)

    # untere Aufnahme Phi36 (Mahlwerk)
    bot = cq.Workplane("XY").circle(B_BOT_BORE_D / 2).extrude(B_BOT_BORE_H)
    body = body.cut(bot)

    # M3-Gewindebohrungen (Kernloch) auf der Ringschulter der unteren Aufnahme
    for x, y in _bolt_circle(B_M3_COUNT, B_M3_BC):
        hole = (cq.Workplane("XY")
                .circle(B_M3_DRILL_D / 2)
                .extrude(B_M3_DEPTH)
                .translate((x, y, B_BOT_BORE_H)))
        body = body.cut(hole)

    return body


# ===================================================================
#  VORSCHAU-GRAFIK (optional, nur wenn matplotlib vorhanden)
# ===================================================================

def _mesh(part, z_off=0.0):
    import numpy as np
    verts, tris = part.val().translate((0, 0, z_off)).tessellate(0.2)
    return (np.array([(p.x, p.y, p.z) for p in verts]), np.array(tris))


def _draw(ax, meshes):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np
    allv = []
    for v, f, color in meshes:
        ax.add_collection3d(Poly3DCollection(
            v[f], facecolor=color, edgecolor=(0, 0, 0, 0.25), linewidth=0.1))
        allv.append(v)
    allv = np.vstack(allv)
    mn, mx = allv.min(axis=0), allv.max(axis=0)
    ctr, span = (mn + mx) / 2, (mx - mn).max() / 2
    ax.set_xlim(ctr[0] - span, ctr[0] + span)
    ax.set_ylim(ctr[1] - span, ctr[1] + span)
    ax.set_zlim(ctr[2] - span, ctr[2] + span)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=22, azim=-58)
    ax.set_xlabel("X [mm]")
    ax.set_ylabel("Y [mm]")
    ax.set_zlabel("Z [mm]")


def _half(part):
    """Schneidet die Haelfte x>0 weg -> Schnittflaeche liegt in der XZ-Ebene."""
    cutter = cq.Workplane("XY").box(1000, 1000, 1000).translate((-500, 0, 0))
    return part.intersect(cutter)


def render_preview(head, body, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib nicht vorhanden - Vorschau uebersprungen")
        return

    orange, gray = (0.85, 0.55, 0.20), (0.70, 0.70, 0.72)
    head_lift = B_TOTAL_H - H_SPIGOT_H
    head_s, body_s = _half(head), _half(body)

    fig = plt.figure(figsize=(15, 11))

    # --- Zeile 1: Aussenansicht ---
    ax = fig.add_subplot(2, 3, 1, projection="3d")
    _draw(ax, [(*_mesh(head), orange)])
    ax.set_title("Kopf - Aussenansicht")

    ax = fig.add_subplot(2, 3, 2, projection="3d")
    _draw(ax, [(*_mesh(body), gray)])
    ax.set_title("Body - Aussenansicht")

    ax = fig.add_subplot(2, 3, 3, projection="3d")
    _draw(ax, [(*_mesh(body), gray), (*_mesh(head, head_lift), orange)])
    ax.set_title("Baugruppe - zusammengesteckt")

    # --- Zeile 2: Schnittansicht (zeigt Bohrungen) ---
    ax = fig.add_subplot(2, 3, 4, projection="3d")
    _draw(ax, [(*_mesh(head_s), orange)])
    ax.set_title("Kopf - Schnitt")

    ax = fig.add_subplot(2, 3, 5, projection="3d")
    _draw(ax, [(*_mesh(body_s), gray)])
    ax.set_title("Body - Schnitt")

    ax = fig.add_subplot(2, 3, 6, projection="3d")
    _draw(ax, [(*_mesh(body_s), gray), (*_mesh(head_s, head_lift), orange)])
    ax.set_title("Baugruppe - Schnitt")

    fig.suptitle("Pfeffermuehle - CAD-Vorschau (Masse in mm)", fontsize=15)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print("geschrieben:", path)


# ===================================================================
#  EXPORT
# ===================================================================

def render_drawing(path):
    """Saubere 2D-Schnittzeichnung mit Bemassung zum Abgleich mit der Skizze."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError:
        print("matplotlib nicht vorhanden - Zeichnung uebersprungen")
        return

    # (z_unten, z_oben, r_innen, r_aussen)
    head_bands = [
        (0,  H_SPIGOT_H,                 H_BOT_RECESS_D / 2, H_SPIGOT_D / 2),
        (H_SPIGOT_H, H_BOT_RECESS_H,     H_BOT_RECESS_D / 2, H_OUTER_D / 2),
        (H_BOT_RECESS_H, H_TOTAL_H - H_TOP_CBORE_H,
                                         H_CENTER_HOLE_D / 2, H_OUTER_D / 2),
        (H_TOTAL_H - H_TOP_CBORE_H, H_TOTAL_H,
                                         H_TOP_CBORE_D / 2, H_OUTER_D / 2),
    ]
    head_holes = [(H_BOT_RECESS_H, H_BOT_RECESS_H + H_M3_DEPTH,
                   H_M3_BC / 2 - H_M3_DRILL_D / 2, H_M3_BC / 2 + H_M3_DRILL_D / 2)]

    body_bands = [
        (0, B_BOT_BORE_H,                B_BOT_BORE_D / 2, B_OUTER_D / 2),
        (B_BOT_BORE_H, B_TOTAL_H - B_TOP_BORE_H,
                                         B_MAIN_BORE_D / 2, B_OUTER_D / 2),
        (B_TOTAL_H - B_TOP_BORE_H, B_TOTAL_H,
                                         B_TOP_BORE_D / 2, B_OUTER_D / 2),
    ]
    body_holes = [(B_BOT_BORE_H, B_BOT_BORE_H + B_M3_DEPTH,
                   B_M3_BC / 2 - B_M3_DRILL_D / 2, B_M3_BC / 2 + B_M3_DRILL_D / 2)]

    def vdim(ax, x, z0, z1, text):
        ax.annotate("", (x, z0), (x, z1),
                    arrowprops=dict(arrowstyle="<->", color="b"))
        ax.text(x + 1.5, (z0 + z1) / 2, text, color="b",
                va="center", fontsize=8)

    def hdim(ax, z, r, text):
        ax.annotate("", (-r, z), (r, z),
                    arrowprops=dict(arrowstyle="<->", color="b"))
        ax.text(0, z + 1.2, text, color="b", ha="center", fontsize=8)

    def callout(ax, xy, text, xytext):
        ax.annotate(text, xy=xy, xytext=xytext, fontsize=8, color="b",
                    arrowprops=dict(arrowstyle="->", color="b"))

    def draw_part(ax, title, bands, holes, total_h):
        for z0, z1, ri, ro in bands:
            for sx in (-1, 1):
                lo = min(sx * ri, sx * ro)
                ax.add_patch(Rectangle((lo, z0), ro - ri, z1 - z0,
                                       facecolor="0.8", edgecolor="k", lw=1.2))
        for z0, z1, ri, ro in holes:
            for sx in (-1, 1):
                lo = min(sx * ri, sx * ro)
                ax.add_patch(Rectangle((lo, z0), ro - ri, z1 - z0,
                                       facecolor="white", edgecolor="k",
                                       lw=1.0, ls="--"))
        ax.axvline(0, color="r", lw=0.8, ls="-.")
        ax.set_title(title)
        ax.set_aspect("equal")
        ax.set_xlabel("r [mm]")
        ax.set_ylabel("z [mm]")
        ax.set_ylim(-14, total_h + 14)
        ax.set_xlim(-34, 40)
        ax.grid(True, ls=":", alpha=0.4)

    fig, (axh, axb) = plt.subplots(1, 2, figsize=(13, 9))

    # ---- Kopf ----
    draw_part(axh, "KOPF (oberes Teil) - Schnitt", head_bands, head_holes,
              H_TOTAL_H)
    hdim(axh, H_TOTAL_H + 6, H_OUTER_D / 2, f"Ø{H_OUTER_D:g}")
    hdim(axh, -6, H_SPIGOT_D / 2, f"Ø{H_SPIGOT_D:g}")
    vdim(axh, 27, 0, H_TOTAL_H, f"{H_TOTAL_H:g}")
    vdim(axh, 21, 0, H_SPIGOT_H, f"{H_SPIGOT_H:g}")
    vdim(axh, 21, H_TOTAL_H - H_TOP_CBORE_H, H_TOTAL_H, f"{H_TOP_CBORE_H:g}")
    callout(axh, (0, H_TOTAL_H), f"Ø{H_TOP_CBORE_D:g}", (-30, H_TOTAL_H + 8))
    callout(axh, (H_CENTER_HOLE_D / 2, 12), f"Ø{H_CENTER_HOLE_D:g}",
            (-30, 14))
    callout(axh, (H_BOT_RECESS_D / 2, 2.5), f"Ø{H_BOT_RECESS_D:g}",
            (-30, 2))
    callout(axh, (H_M3_BC / 2, H_BOT_RECESS_H + H_M3_DEPTH / 2),
            f"2x M3x8\nLochkreis Ø{H_M3_BC:g}", (24, 18))

    # ---- Body ----
    draw_part(axb, "BODY (unteres Teil) - Schnitt", body_bands, body_holes,
              B_TOTAL_H)
    hdim(axb, B_TOTAL_H + 6, B_OUTER_D / 2, f"Ø{B_OUTER_D:g}")
    vdim(axb, 27, 0, B_TOTAL_H, f"{B_TOTAL_H:g}")
    vdim(axb, 24, B_TOTAL_H - B_TOP_BORE_H, B_TOTAL_H, f"{B_TOP_BORE_H:g}")
    vdim(axb, 24, 0, B_BOT_BORE_H, f"{B_BOT_BORE_H:g}")
    callout(axb, (B_TOP_BORE_D / 2, B_TOTAL_H - 4), f"Ø{B_TOP_BORE_D:g}",
            (-32, B_TOTAL_H - 2))
    callout(axb, (B_MAIN_BORE_D / 2, B_TOTAL_H / 2), f"Ø{B_MAIN_BORE_D:g}",
            (-32, B_TOTAL_H / 2))
    callout(axb, (B_BOT_BORE_D / 2, 4), f"Ø{B_BOT_BORE_D:g}", (-32, 2))
    callout(axb, (B_M3_BC / 2, B_BOT_BORE_H + B_M3_DEPTH / 2),
            f"2x M3x8\nLochkreis Ø{B_M3_BC:g}", (24, 30))

    fig.suptitle("Pfeffermuehle - Schnittzeichnung (alle Masse in mm)",
                 fontsize=14)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print("geschrieben:", path)


def main():
    head = make_head()
    body = make_body()

    exports = {
        "pepper_mill_head.step": head,
        "pepper_mill_body.step": body,
        "pepper_mill_head.stl": head,
        "pepper_mill_body.stl": body,
    }
    for name, part in exports.items():
        cq.exporters.export(part, os.path.join(OUT, name))
        print("geschrieben:", name)

    # Baugruppe: Kopf auf den Body gesteckt
    head_lift = B_TOTAL_H - H_SPIGOT_H
    assy = cq.Assembly(name="Pfeffermuehle")
    assy.add(body, name="Body", color=cq.Color(0.7, 0.7, 0.72))
    assy.add(head, name="Kopf", color=cq.Color(0.85, 0.55, 0.20),
             loc=cq.Location(cq.Vector(0, 0, head_lift)))
    assy.export(os.path.join(OUT, "pepper_mill_assembly.step"))
    print("geschrieben: pepper_mill_assembly.step")

    render_preview(head, body, os.path.join(OUT, "preview.png"))
    render_drawing(os.path.join(OUT, "drawing.png"))


if __name__ == "__main__":
    main()
