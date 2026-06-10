"""
Design system Arc-inspired — dark sobre + accent indigo/violet
+ formes complexes via flet.canvas (sparkline, ring, arc, dots timeline).

Usage :
    from vues.theme import C, FONT, card, chip, section_header
    from vues.theme import sparkline, ring_chart, dots_timeline
    from vues.theme import view_root  # wrapper de page avec ambient bg
"""

import math

import flet as ft
from flet import canvas as cv


# =====================================================================
# PALETTE — Arc Dark inspired (avec plus de présence indigo)
# =====================================================================

class C:
    # Surfaces (légère teinte indigo, plus chaud que pur noir)
    bg            = "#0B0B14"   # fond global (très subtile teinte indigo)
    bg_elevated   = "#171724"   # cards
    bg_subtle     = "#1F1F2E"   # inputs, alternatives
    bg_hover      = "#252535"

    # Bordures
    border        = "#2E2E42"   # un peu plus marquée
    border_subtle = "#1F1F2E"
    border_accent = "#3E3470"   # bordure avec teinte indigo

    # Texte
    text          = "#F5F5F7"
    text_muted    = "#A1A1B5"   # un peu plus chaud
    text_subtle   = "#71718A"

    # Accent Arc-like (violet/indigo plus saturé et présent)
    accent        = "#A78BFA"   # primary
    accent_strong = "#7C3AED"   # version saturée
    accent_soft   = "#C4B5FD"   # version pâle
    accent_glow   = "#6D28D9"   # version profonde pour les fonds

    # Sémantiques sobres
    success       = "#34D399"
    warning       = "#FBBF24"
    danger        = "#F87171"
    info          = "#60A5FA"

    # Gradients ambient (utilisés en haut de page)
    grad_top_a    = "#2E1065"   # violet/indigo profond
    grad_top_b    = "#1E1B4B"   # indigo nuit
    grad_bottom   = "#0B0B14"   # fond


# Tailles typographiques
class FONT:
    display = 32
    h1      = 24
    h2      = 18
    h3      = 16
    body    = 14
    small   = 12
    micro   = 11


# =====================================================================
# COMPOSANTS — réutilisables partout
# =====================================================================

def card(content, padding=18, radius=20, bg=None, border=True,
         on_click=None, shadow=True, expand=False, accent=False):
    """Card sobre style Arc. Si accent=True, bordure gauche violet visible."""
    if accent:
        border_obj = ft.Border(
            top=ft.BorderSide(1, C.border),
            bottom=ft.BorderSide(1, C.border),
            left=ft.BorderSide(3, C.accent),
            right=ft.BorderSide(1, C.border),
        )
    elif border:
        border_obj = ft.Border(
            top=ft.BorderSide(1, C.border),
            bottom=ft.BorderSide(1, C.border),
            left=ft.BorderSide(1, C.border),
            right=ft.BorderSide(1, C.border),
        )
    else:
        border_obj = None

    return ft.Container(
        content=content,
        padding=padding,
        border_radius=radius,
        bgcolor=bg or C.bg_elevated,
        ink=on_click is not None,
        on_click=on_click,
        expand=expand,
        border=border_obj,
        shadow=ft.BoxShadow(
            blur_radius=24,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.35, "#000000"),
            offset=ft.Offset(0, 8),
        ) if shadow else None,
    )


def chip(text, color=None, bg=None):
    """Pill discrète."""
    return ft.Container(
        padding=ft.Padding(left=10, top=4, right=10, bottom=4),
        border_radius=999,
        bgcolor=bg or C.bg_subtle,
        border=ft.Border(
            top=ft.BorderSide(1, C.border_subtle),
            bottom=ft.BorderSide(1, C.border_subtle),
            left=ft.BorderSide(1, C.border_subtle),
            right=ft.BorderSide(1, C.border_subtle),
        ),
        content=ft.Text(text, size=FONT.micro, color=color or C.text_muted,
                        weight=ft.FontWeight.W_500),
    )


def accent_chip(text, color=None):
    """Chip avec accent (pour les compteurs / badges)."""
    c = color or C.accent
    return ft.Container(
        padding=ft.Padding(left=10, top=4, right=10, bottom=4),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.15, c),
        content=ft.Text(text, size=FONT.micro, color=c,
                        weight=ft.FontWeight.W_600),
    )


def section_header(title, subtitle=None, action=None):
    """Titre de section sobre."""
    left = ft.Column(
        spacing=2, expand=True,
        controls=[
            ft.Text(title, size=FONT.h2, weight=ft.FontWeight.W_700,
                    color=C.text),
            *([ft.Text(subtitle, size=FONT.small, color=C.text_subtle)]
              if subtitle else []),
        ],
    )
    items = [left]
    if action is not None:
        items.append(action)
    return ft.Container(
        padding=ft.Padding(left=2, top=8, right=2, bottom=10),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=items,
        ),
    )


def pill_button(text, icon=None, on_click=None, primary=True,
                expand=False, color=None):
    """Bouton pilule (style Arc)."""
    if primary:
        bg = color or C.accent_strong
        fg = "#FFFFFF"
    else:
        bg = C.bg_subtle
        fg = C.text

    row_children = []
    if icon is not None:
        row_children.append(ft.Icon(icon, color=fg, size=16))
    row_children.append(
        ft.Text(text, color=fg, weight=ft.FontWeight.W_600, size=FONT.body)
    )

    return ft.Container(
        bgcolor=bg,
        border_radius=999,
        padding=ft.Padding(left=18, top=11, right=18, bottom=11),
        ink=True,
        on_click=on_click,
        expand=expand,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            controls=row_children,
        ),
    )


def appbar(title, back_route=None, page=None, actions=None):
    """AppBar sobre, monochrome, sans elevation."""
    leading = None
    if back_route is not None and page is not None:
        async def _back(e):
            await page.push_route(back_route)
        leading = ft.IconButton(
            icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
            icon_color=C.text_muted,
            icon_size=18,
            on_click=_back,
        )

    return ft.AppBar(
        leading=leading,
        title=ft.Text(title, color=C.text,
                      weight=ft.FontWeight.W_600, size=FONT.h3),
        bgcolor=C.bg,
        elevation=0,
        actions=actions or [],
        center_title=False,
    )


def divider(opacity=1.0):
    return ft.Container(
        height=1,
        bgcolor=ft.Colors.with_opacity(opacity, C.border_subtle),
    )


# =====================================================================
# GRAPHIQUES — formes complexes via flet.canvas
# =====================================================================

def sparkline(values, color=None, width=300, height=72,
              fill_below=True, smooth=True):
    """
    Courbe lisse (cubic bezier) optionnellement remplie en dessous.
    Style Arc : trait fin, aire dégradée très subtile.
    """
    if not values or len(values) < 2:
        return ft.Container(width=width, height=height,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text("—", color=C.text_subtle,
                                            size=FONT.small))

    color = color or C.accent
    vmin, vmax = min(values), max(values)
    rng = (vmax - vmin) or 1.0
    pad_y = 8
    pad_x = 2
    n = len(values)

    def xx(i):
        return pad_x + (i / (n - 1)) * (width - 2 * pad_x)

    def yy(v):
        return pad_y + (1 - (v - vmin) / rng) * (height - 2 * pad_y)

    # Construire les points
    pts = [(xx(i), yy(v)) for i, v in enumerate(values)]

    # Path de la ligne (cubic bezier lissé)
    line_elems = [cv.Path.MoveTo(*pts[0])]
    if smooth and len(pts) >= 3:
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            # Control points : mid-x pour lissage doux
            cx = (x0 + x1) / 2
            line_elems.append(
                cv.Path.CubicTo(cx, y0, cx, y1, x1, y1)
            )
    else:
        for x, y in pts[1:]:
            line_elems.append(cv.Path.LineTo(x, y))

    line_paint = ft.Paint(
        color=color,
        stroke_width=2.2,
        style=ft.PaintingStyle.STROKE,
    )

    shapes = []

    # Aire sous la courbe avec gradient si demandé
    if fill_below:
        area_elems = list(line_elems)  # même chemin que la ligne
        area_elems.append(cv.Path.LineTo(pts[-1][0], height - pad_y))
        area_elems.append(cv.Path.LineTo(pts[0][0], height - pad_y))
        area_elems.append(cv.Path.Close())

        try:
            area_paint = ft.Paint(
                gradient=ft.PaintLinearGradient(
                    begin=ft.Offset(0, 0),
                    end=ft.Offset(0, height),
                    colors=[
                        ft.Colors.with_opacity(0.30, color),
                        ft.Colors.with_opacity(0.00, color),
                    ],
                ),
                style=ft.PaintingStyle.FILL,
            )
        except Exception:
            # Fallback : couleur plate semi-transparente
            area_paint = ft.Paint(
                color=ft.Colors.with_opacity(0.12, color),
                style=ft.PaintingStyle.FILL,
            )

        shapes.append(cv.Path(elements=area_elems, paint=area_paint))

    shapes.append(cv.Path(elements=line_elems, paint=line_paint))

    return cv.Canvas(width=width, height=height, shapes=shapes)


def ring_chart(value, total=100, color=None, size=72, stroke=8,
               label=None, sub=None):
    """
    Donut chart minimaliste façon Arc.
    Affiche en centre la valeur (label) + sous-titre (sub).
    """
    color = color or C.accent
    pct = max(0.0, min(1.0, (value / total) if total else 0))

    cx = cy = size / 2
    r = (size - stroke) / 2

    # Anneau de fond
    bg_arc = cv.Arc(
        x=stroke / 2, y=stroke / 2,
        width=size - stroke, height=size - stroke,
        start_angle=0, sweep_angle=2 * math.pi,
        paint=ft.Paint(
            color=C.border,
            stroke_width=stroke,
            style=ft.PaintingStyle.STROKE,
        ),
    )

    # Arc valeur (depuis -90° = haut)
    val_arc = cv.Arc(
        x=stroke / 2, y=stroke / 2,
        width=size - stroke, height=size - stroke,
        start_angle=-math.pi / 2,
        sweep_angle=2 * math.pi * pct,
        paint=ft.Paint(
            color=color,
            stroke_width=stroke,
            style=ft.PaintingStyle.STROKE,
            stroke_cap=ft.StrokeCap.ROUND,
        ),
    )

    canvas = cv.Canvas(
        width=size, height=size,
        shapes=[bg_arc, val_arc],
    )

    # Stack avec label centré
    label_widget = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
        controls=[
            ft.Text(label if label is not None else str(value),
                    color=C.text, weight=ft.FontWeight.W_700,
                    size=int(size / 4)),
            *([ft.Text(sub, color=C.text_subtle, size=FONT.micro)]
              if sub else []),
        ],
    )

    return ft.Stack(
        width=size, height=size,
        controls=[
            canvas,
            ft.Container(width=size, height=size,
                         alignment=ft.Alignment.CENTER,
                         content=label_widget),
        ],
    )


def dots_timeline(nodes, width=300, height=72, color=None):
    """
    Mini timeline horizontale : suite de points reliés par une ligne fine.
    nodes : liste de dicts {label?, accent?} — l'ordre = ordre temporel.
    """
    color = color or C.accent
    n = max(1, len(nodes))

    pad_x = 14
    cy = height / 2 - 6  # un peu remontée pour laisser place aux labels

    if n == 1:
        points_x = [width / 2]
    else:
        points_x = [pad_x + (i / (n - 1)) * (width - 2 * pad_x)
                    for i in range(n)]

    shapes = []

    # Ligne reliant les points
    if n >= 2:
        line_elems = [cv.Path.MoveTo(points_x[0], cy)]
        for x in points_x[1:]:
            line_elems.append(cv.Path.LineTo(x, cy))
        shapes.append(cv.Path(
            elements=line_elems,
            paint=ft.Paint(
                color=ft.Colors.with_opacity(0.5, C.border),
                stroke_width=1.5,
                style=ft.PaintingStyle.STROKE,
            ),
        ))

    # Points (outer ring + inner dot pour effet "node")
    for i, x in enumerate(points_x):
        is_accent = nodes[i].get("accent", False)
        c = color if is_accent else C.text_subtle
        # Halo
        shapes.append(cv.Circle(
            x=x, y=cy, radius=8,
            paint=ft.Paint(color=ft.Colors.with_opacity(0.18, c),
                           style=ft.PaintingStyle.FILL),
        ))
        # Centre
        shapes.append(cv.Circle(
            x=x, y=cy, radius=4,
            paint=ft.Paint(color=c, style=ft.PaintingStyle.FILL),
        ))

    return ft.Column(
        spacing=4,
        controls=[
            cv.Canvas(width=width, height=int(cy + 12), shapes=shapes),
            ft.Container(
                width=width,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Container(
                            width=(width / n) - 4,
                            content=ft.Text(
                                n_data.get("label", ""),
                                color=C.text_muted, size=FONT.micro,
                                text_align=ft.TextAlign.CENTER,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        )
                        for n_data in nodes
                    ],
                ),
            ),
        ],
    )


def stat_arc(label, value, sub=None, color=None, size=110):
    """
    Card stat avec ring arc en fond, gros chiffre, label.
    """
    color = color or C.accent
    return card(
        padding=18,
        content=ft.Column(
            spacing=12,
            controls=[
                ring_chart(value=1, total=1, color=color, size=size,
                           stroke=6, label=str(value), sub=None),
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(label, size=FONT.small, color=C.text_muted,
                                weight=ft.FontWeight.W_500),
                        *([ft.Text(sub, size=FONT.micro, color=C.text_subtle)]
                          if sub else []),
                    ],
                ),
            ],
        ),
    )


def ambient_bg(child, height=None):
    """
    Conteneur avec un dégradé radial/linéaire très subtil en fond (Arc-like).
    """
    return ft.Container(
        height=height,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[C.grad_top_a, C.grad_bottom],
            stops=[0.0, 0.6],
        ),
        content=child,
    )


def page_root(content):
    """
    Wrapper de toute une vue : pose un grand halo violet/indigo très diffus
    en haut, puis le fond se fond vers le noir-indigo bg.
    Utilise un Stack avec un overlay gradient absolu pour l'ambiance Arc.
    """
    halo = ft.Container(
        height=420,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER,
            end=ft.Alignment.BOTTOM_CENTER,
            colors=[
                ft.Colors.with_opacity(0.28, C.accent_glow),
                ft.Colors.with_opacity(0.06, C.accent_glow),
                ft.Colors.with_opacity(0.0, C.bg),
            ],
            stops=[0.0, 0.5, 1.0],
        ),
    )
    return ft.Stack(
        expand=True,
        controls=[
            # halo en haut
            ft.Container(
                left=0, right=0, top=0,
                content=halo,
            ),
            # contenu réel par-dessus
            content,
        ],
    )