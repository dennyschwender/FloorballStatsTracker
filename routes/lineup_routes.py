"""
Lineup view and export routes blueprint
"""
import io
from flask import Blueprint, request, render_template, send_file
from services.game_service import load_games, find_game_by_id
from models.roster import load_roster

lineup_bp = Blueprint('lineup', __name__)


def _lineup_context(game_id):
    """Shared helper: load game + roster for lineup views."""
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return None, None, None
    roster = []
    if game.get('team'):
        season = game.get('season', '')
        roster = load_roster(game['team'], season) if season else load_roster(game['team'])
    player_map = {}
    for player in roster:
        key = f"{player['number']} - {player['surname']} {player['name']}"
        player_map[key] = player
    return game, roster, player_map


@lineup_bp.route('/game/<int:game_id>/lineup')
def view_game_lineup(game_id):
    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404
    return render_template('game_lineup.html', game=game, roster=roster, player_map=player_map)


@lineup_bp.route('/game/<int:game_id>/lineup/eink')
def view_game_lineup_eink(game_id):
    """E-ink friendly paginated lineup view."""
    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404
    return render_template('game_lineup_eink.html', game=game, roster=roster, player_map=player_map)


# ── Device profiles for e-reader PDF export ────────────────────────────────
# Page dimensions are the physical screen area.
# Tolino Shine (6"): 1448×1072 px @ 300 ppi → ~122.7×90.7 mm
# Xteink X4 (4.3"): 800×600 px portrait @ ~233 ppi → ~87×65 mm
_EINK_DEVICES = {
    'tolino': dict(
        label='Tolino Shine',
        # ── PDF (mm) ────────────────────────────────────────────────────────
        page_w=90, page_h=122, margin=7,
        title_fs=20, vs_fs=13, section_fs=16,
        meta_fs=12, player_fs=14,
        toc_title_fs=13, toc_item_fs=12,
        num_w=14, meta_label_w=18,
        cell_pad=5, hr_thick=1.5,
        spec_spacer=5,
        # ── EPUB fixed-layout (CSS px) ──────────────────────────────────────
        epub_vw=600, epub_vh=800,
        epub_title_fs=28, epub_vs_fs=16, epub_section_fs=20,
        epub_meta_fs=14, epub_player_fs=15, epub_toc_fs=13,
        epub_pad=8, epub_row_pad=3,
        epub_lines_per_page=1,
    ),
    'xteink': dict(
        label='Xteink X4',
        # ── PDF (mm) ────────────────────────────────────────────────────────
        page_w=65, page_h=87, margin=5,
        title_fs=14, vs_fs=9, section_fs=11,
        meta_fs=9, player_fs=10,
        toc_title_fs=9, toc_item_fs=9,
        num_w=10, meta_label_w=13,
        cell_pad=3, hr_thick=1.0,
        spec_spacer=3,
        # ── EPUB fixed-layout (CSS px) ──────────────────────────────────────
        epub_vw=400, epub_vh=533,
        epub_title_fs=17, epub_vs_fs=10, epub_section_fs=13,
        epub_meta_fs=10, epub_player_fs=11, epub_toc_fs=10,
        epub_pad=5, epub_row_pad=1,
        epub_lines_per_page=2,
        # explicit page grouping (keys: 'goalies', 'line:N', spec key names)
        epub_page_groups=[
            ['line:0', 'line:1', 'line:2'],
            ['line:3', 'goalies'],
            ['pp1', 'pp2', '6vs5'],
            ['bp1', 'bp2', 'stress_line'],
        ],
    ),
}


@lineup_bp.route('/game/<int:game_id>/lineup/pdf')
def download_lineup_pdf(game_id):
    """Generate an e-reader PDF of the lineup.  ?device=tolino|xteink"""
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        HRFlowable,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER

    device_key = request.args.get('device', 'tolino')
    p = _EINK_DEVICES.get(device_key, _EINK_DEVICES['tolino'])

    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404

    # ── Page geometry ────────────────────────────────────────────────────────
    PAGE_W = p['page_w'] * mm
    PAGE_H = p['page_h'] * mm
    MARGIN = p['margin'] * mm
    COL_W  = PAGE_W - 2 * MARGIN
    NUM_W  = p['num_w'] * mm
    PAD    = p['cell_pad']

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )

    # ── Styles ───────────────────────────────────────────────────────────────
    def _ps(name, font='Helvetica', size=10, align=None, **kw):
        kwargs = dict(fontName=font, fontSize=size, leading=round(size * 1.25))
        if align is not None:
            kwargs['alignment'] = align
        kwargs.update(kw)
        return ParagraphStyle(name, **kwargs)

    title_style     = _ps('T', 'Helvetica-Bold', p['title_fs'],    TA_CENTER,
                          spaceAfter=2 * mm)
    vs_style        = _ps('V', 'Helvetica',      p['vs_fs'],       TA_CENTER,
                          spaceAfter=2 * mm)
    section_style   = _ps('S', 'Helvetica-Bold', p['section_fs'],
                          spaceAfter=2 * mm, spaceBefore=1 * mm)
    meta_lbl_style  = _ps('ML', 'Helvetica-Bold', p['meta_fs'])
    meta_val_style  = _ps('MV', 'Helvetica',       p['meta_fs'])
    player_style    = _ps('PV', 'Helvetica',        p['player_fs'])
    player_bold     = _ps('PB', 'Helvetica-Bold',   p['player_fs'])
    toc_title_style = _ps('TT', 'Helvetica-Bold', p['toc_title_fs'],
                          spaceBefore=2 * mm, spaceAfter=1 * mm)
    toc_item_style  = _ps('TI', 'Helvetica',      p['toc_item_fs'])

    def hr():
        return HRFlowable(width='100%', thickness=p['hr_thick'],
                          color=colors.black, spaceAfter=1.5 * mm, spaceBefore=0)

    def fmt_player(s):
        parts = s.split(' - ', 1)
        num   = parts[0].strip() if len(parts) > 1 else ''
        full  = parts[1].strip() if len(parts) > 1 else s.strip()
        words = full.split()
        name  = (words[0] + ' ' + words[1][0] + '.') if len(words) > 1 else full
        return num, name

    def player_table(players):
        rows = [[Paragraph(num, player_bold), Paragraph(nm, player_style)]
                for num, nm in (fmt_player(pl) for pl in players)]
        if not rows:
            return None
        tbl = Table(rows, colWidths=[NUM_W, COL_W - NUM_W])
        tbl.setStyle(TableStyle([
            ('FONTSIZE',      (0, 0), (-1, -1), p['player_fs']),
            ('ALIGN',         (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN',         (1, 0), (1, -1), 'LEFT'),
            ('TOPPADDING',    (0, 0), (-1, -1), PAD),
            ('BOTTOMPADDING', (0, 0), (-1, -1), PAD),
            ('LINEBELOW',     (0, 0), (-1, -2), 0.5, colors.black),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return tbl

    # ── Content helpers ──────────────────────────────────────────────────────
    SPEC_KEYS = [
        ('pp1', 'PP1'), ('pp2', 'PP2'),
        ('bp1', 'BP1'), ('bp2', 'BP2'),
        ('6vs5', '6 vs 5'), ('stress_line', 'Stress Line'),
    ]
    spec    = [(label, game[k]) for k, label in SPEC_KEYS if game.get(k)]
    goalies = game.get('goalies', [])
    lines   = [l for l in game.get('lines', []) if l]

    toc_entries = ['Game Info']
    if goalies:
        toc_entries.append('Goalies')
    for i in range(len(lines)):
        toc_entries.append(f'Line {i + 1}')
    for i in range(0, len(spec), 2):
        toc_entries.append(' / '.join(lbl for lbl, _ in spec[i:i + 2]))

    story = []

    # ── Cover ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(game.get('home_team', ''), title_style))
    story.append(Paragraph('vs', vs_style))
    story.append(Paragraph(game.get('away_team', ''), title_style))
    story.append(hr())

    meta_rows = []
    for key, label in [('date', 'Date'), ('team', 'Team'),
                       ('season', 'Season')]:
        if game.get(key):
            meta_rows.append([Paragraph(f'<b>{label}</b>', meta_lbl_style),
                              Paragraph(game[key], meta_val_style)])
    refs = ', '.join(r for r in [game.get('referee1', ''),
                                  game.get('referee2', '')] if r)
    if refs:
        meta_rows.append([Paragraph('<b>Refs</b>', meta_lbl_style),
                          Paragraph(refs, meta_val_style)])
    if meta_rows:
        lw = p['meta_label_w'] * mm
        mt = Table(meta_rows, colWidths=[lw, COL_W - lw])
        mt.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), PAD),
            ('BOTTOMPADDING', (0, 0), (-1, -1), PAD),
            ('LINEBELOW',     (0, 0), (-1, -1), 0.4, colors.grey),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(mt)
        story.append(Spacer(1, 2 * mm))

    story.append(Paragraph('Contents', toc_title_style))
    for idx, entry in enumerate(toc_entries):
        story.append(Paragraph(f'{idx + 1}.  {entry}', toc_item_style))

    # ── Goalies ──────────────────────────────────────────────────────────────
    if goalies:
        story.append(PageBreak())
        story.append(Paragraph('Goalies', section_style))
        story.append(hr())
        tbl = player_table(goalies)
        if tbl:
            story.append(tbl)

    # ── Lines (one per page) ─────────────────────────────────────────────────
    for i, line in enumerate(lines):
        story.append(PageBreak())
        story.append(Paragraph(f'Line {i + 1}', section_style))
        story.append(hr())
        tbl = player_table(line)
        if tbl:
            story.append(tbl)

    # ── Special formations (2 per page) ──────────────────────────────────────
    for idx in range(0, len(spec), 2):
        story.append(PageBreak())
        for label, players in spec[idx:idx + 2]:
            story.append(Paragraph(label, section_style))
            story.append(hr())
            tbl = player_table(players)
            if tbl:
                story.append(tbl)
            story.append(Spacer(1, p['spec_spacer'] * mm))

    doc.build(story)
    buf.seek(0)
    safe_home = ''.join(c for c in game.get('home_team', 'home')
                        if c.isalnum() or c in '-_')
    safe_away = ''.join(c for c in game.get('away_team', 'away')
                        if c.isalnum() or c in '-_')
    filename = f"lineup_{safe_home}_vs_{safe_away}_{device_key}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)


@lineup_bp.route('/game/<int:game_id>/lineup/epub')
def download_lineup_epub(game_id):
    """Generate a fixed-layout EPUB of the lineup.  ?device=tolino|xteink"""
    import zipfile
    import html as _h

    device_key = request.args.get('device', 'tolino')
    p = _EINK_DEVICES.get(device_key, _EINK_DEVICES['tolino'])

    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404

    VW  = p['epub_vw']
    VH  = p['epub_vh']
    PAD = p['epub_pad']

    def e(s):
        return _h.escape(str(s) if s else '')

    def fmt_player(s):
        parts = s.split(' - ', 1)
        num   = parts[0].strip() if len(parts) > 1 else ''
        full  = parts[1].strip() if len(parts) > 1 else s.strip()
        words = full.split()
        name  = (words[0] + ' ' + words[1][0] + '.') if len(words) > 1 else full
        return num, name

    def players_html(players):
        if not players:
            return ''
        rows = ''.join(
            f'<div class="prow">'
            f'<span class="num">{e(n)}</span>'
            f'<span class="sep"> &#8212; </span>'
            f'<span class="name">{e(nm)}</span>'
            f'</div>'
            for n, nm in (fmt_player(pl) for pl in players)
        )
        return f'<div class="players">{rows}</div>'

    def make_page(body_html, title=''):
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" '
            f'xmlns:epub="http://www.idpf.org/2007/ops">\n'
            f'<head>\n'
            f'  <meta charset="UTF-8"/>\n'
            f'  <meta name="viewport" content="width={VW}, height={VH}"/>\n'
            f'  <title>{e(title)}</title>\n'
            f'  <link rel="stylesheet" type="text/css" href="style.css"/>\n'
            f'</head>\n'
            f'<body><div class="page">{body_html}</div></body>\n'
            f'</html>'
        )

    # ── Content helpers ──────────────────────────────────────────────────────
    SPEC_KEYS = [
        ('pp1', 'PP1'), ('pp2', 'PP2'),
        ('bp1', 'BP1'), ('bp2', 'BP2'),
        ('6vs5', '6 vs 5'), ('stress_line', 'Stress Line'),
    ]
    spec    = [(label, game[k]) for k, label in SPEC_KEYS if game.get(k)]
    goalies = game.get('goalies', [])
    lines   = [l for l in game.get('lines', []) if l]

    pages = []   # (page_id, title, xhtml_string)

    # ── Section lookup: key → (label, players) ───────────────────────────────
    sec = {}
    if goalies:
        sec['goalies'] = ('Goalies', goalies)
    for _i, _ln in enumerate(lines):
        sec[f'line:{_i}'] = (f'Line {_i + 1}', _ln)
    for _k, _lbl in SPEC_KEYS:
        if game.get(_k):
            sec[_k] = (_lbl, game[_k])

    def sec_html(key):
        if key not in sec:
            return ''
        _lbl, _players = sec[key]
        return (f'<h2 class="section">{e(_lbl)}</h2>'
                f'<hr/>{players_html(_players)}')

    page_groups_cfg = p.get('epub_page_groups')   # None → use LPP
    LPP             = p['epub_lines_per_page']

    # ── Build TOC entries from actual groups ─────────────────────────────
    if page_groups_cfg:
        toc_entries = ['Game Info'] + [
            ' / '.join(sec[k][0] for k in grp if k in sec)
            for grp in page_groups_cfg
            if any(k in sec for k in grp)
        ]
    else:
        toc_entries = ['Game Info']
        if goalies:
            toc_entries.append('Goalies')
        for _i in range(0, len(lines), LPP):
            toc_entries.append(
                ' / '.join(f'Line {_i + _j + 1}'
                           for _j in range(min(LPP, len(lines) - _i)))
            )
        spec_labels = [lbl for lbl, _ in spec]
        for _si in range(0, len(spec_labels), LPP):
            toc_entries.append(' / '.join(spec_labels[_si:_si + LPP]))

    # ── Cover ────────────────────────────────────────────────────────────
    meta_rows = ''
    for key, label in [('date', 'Date'), ('team', 'Team'), ('season', 'Season')]:
        if game.get(key):
            meta_rows += (
                f'<div class="mrow">'
                f'<span class="ml">{e(label)}:</span>'
                f'<span class="sep"> </span>'
                f'<span class="mv">{e(game[key])}</span>'
                f'</div>'
            )
    refs = ', '.join(r for r in [game.get('referee1', ''), game.get('referee2', '')] if r)
    if refs:
        meta_rows += (
            f'<div class="mrow">'
            f'<span class="ml">Refs:</span>'
            f'<span class="sep"> </span>'
            f'<span class="mv">{e(refs)}</span>'
            f'</div>'
        )
    toc_items = ''.join(f'<li>{e(entry)}</li>' for entry in toc_entries)
    cover_body = (
        f'<h1 class="title">{e(game.get("home_team", ""))}</h1>'
        f'<div class="vs">vs</div>'
        f'<h1 class="title">{e(game.get("away_team", ""))}</h1>'
        f'<hr/>'
        + (f'<div class="meta">{meta_rows}</div>' if meta_rows else '')
        + f'<div class="toc-h">Contents</div><ol class="toc">{toc_items}</ol>'
    )
    game_title = f"{game.get('home_team', '')} vs {game.get('away_team', '')}"
    pages.append(('page_000', 'Cover', make_page(cover_body, game_title)))

    # ── Content pages ───────────────────────────────────────────────────
    n = 1
    if page_groups_cfg:
        for grp in page_groups_cfg:
            present = [k for k in grp if k in sec]
            if not present:
                continue
            titles = ' / '.join(sec[k][0] for k in present)
            body = '<div class="gap"></div>'.join(sec_html(k) for k in present)
            pages.append((f'page_{n:03d}', titles, make_page(body, titles)))
            n += 1
    else:
        if goalies:
            body = f'<h2 class="section">Goalies</h2><hr/>{players_html(goalies)}'
            pages.append((f'page_{n:03d}', 'Goalies', make_page(body, 'Goalies')))
            n += 1
        for _i in range(0, len(lines), LPP):
            chunk = lines[_i:_i + LPP]
            titles = ' / '.join(f'Line {_i + _j + 1}' for _j in range(len(chunk)))
            body = ''.join(
                f'<h2 class="section">Line {_i + _j + 1}</h2>'
                f'<hr/>{players_html(ln)}<div class="gap"></div>'
                for _j, ln in enumerate(chunk)
            )
            pages.append((f'page_{n:03d}', titles, make_page(body, titles)))
            n += 1
        for _si in range(0, len(spec), LPP):
            chunk = spec[_si:_si + LPP]
            t = ' / '.join(lbl for lbl, _ in chunk)
            body = ''.join(
                f'<h2 class="section">{e(lbl)}</h2><hr/>{players_html(pl)}'
                f'<div class="gap"></div>'
                for lbl, pl in chunk
            )
            pages.append((f'page_{n:03d}', t, make_page(body, t)))
            n += 1

    # ── CSS ──────────────────────────────────────────────────────────────────
    tf = p['epub_title_fs']; vsf = p['epub_vs_fs']; sf = p['epub_section_fs']
    mf = p['epub_meta_fs'];  pf  = p['epub_player_fs'];  tf2 = p['epub_toc_fs']
    RP = p['epub_row_pad']
    css = f'''
* {{box-sizing:border-box;margin:0;padding:0;}}
body {{width:{VW}px;height:{VH}px;overflow:hidden;
  font-family:'Courier New',Courier,monospace;background:#fff;color:#000;}}
.page {{width:{VW}px;height:{VH}px;padding:{PAD}px;overflow:hidden;}}
h1.title {{font-size:{tf}px;text-align:center;font-weight:bold;
  line-height:1.2;margin-bottom:{RP}px;}}
.vs {{font-size:{vsf}px;text-align:center;margin-bottom:{RP}px;}}
h2.section {{display:block;font-size:{sf}px;font-weight:bold;
  margin-bottom:{RP}px;margin-top:{RP * 2}px;}}
h2.section:first-child {{margin-top:0;}}
hr {{border:none;border-top:2px solid #000;margin:{RP}px 0;}}
.meta {{display:block;font-size:{mf}px;margin-bottom:{RP * 2}px;}}
.mrow {{display:block;padding:{RP}px 0;border-bottom:1px solid #ccc;
  line-height:1.3;}}
.ml {{display:inline;font-weight:bold;}}
.mv {{display:inline;}}
.toc-h {{display:block;font-size:{tf2}px;font-weight:bold;
  margin-top:{PAD}px;margin-bottom:{RP}px;}}
ol.toc {{font-size:{tf2}px;padding-left:18px;line-height:1.5;}}
.players {{display:block;font-size:{pf}px;}}
.prow {{display:block;padding:{RP}px 0;border-bottom:1px solid #000;
  line-height:1.3;}}
.prow:last-child {{border-bottom:none;}}
.num {{display:inline;font-weight:bold;}}
.sep {{display:inline;}}
.name {{display:inline;}}
.gap {{display:block;height:{RP * 3}px;}}
'''

    # ── EPUB XML ─────────────────────────────────────────────────────────────
    container_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles>'
        '<rootfile full-path="OEBPS/content.opf"'
        ' media-type="application/oebps-package+xml"/>'
        '</rootfiles></container>'
    )

    manifest_pages = '\n'.join(
        f'    <item id="{pid}" href="{pid}.xhtml"'
        f' media-type="application/xhtml+xml"/>'
        for pid, _, _ in pages
    )
    spine_items = '\n'.join(
        f'    <itemref idref="{pid}"'
        f' properties="rendition:page-spread-center"/>'
        for pid, _, _ in pages
    )
    ht = e(game.get('home_team', ''))
    at = e(game.get('away_team', ''))
    opf = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<package xmlns="http://www.idpf.org/2007/opf"'
        f' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        f' version="3.0" unique-identifier="uid">'
        f'<metadata>'
        f'<dc:identifier id="uid">lineup-{game_id}-{device_key}</dc:identifier>'
        f'<dc:title>{ht} vs {at}</dc:title>'
        f'<dc:language>en</dc:language>'
        f'<meta property="rendition:layout">pre-paginated</meta>'
        f'<meta property="rendition:spread">none</meta>'
        f'<meta property="rendition:viewport">width={VW}, height={VH}</meta>'
        f'</metadata>'
        f'<manifest>'
        f'<item id="nav" href="nav.xhtml"'
        f' media-type="application/xhtml+xml" properties="nav"/>'
        f'<item id="style" href="style.css" media-type="text/css"/>'
        f'{manifest_pages}'
        f'</manifest>'
        f'<spine>{spine_items}</spine>'
        f'</package>'
    )

    nav_items = '\n'.join(
        f'  <li><a href="{pid}.xhtml">{e(ptitle)}</a></li>'
        for pid, ptitle, _ in pages
    )
    nav = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<!DOCTYPE html>'
        f'<html xmlns="http://www.w3.org/1999/xhtml"'
        f' xmlns:epub="http://www.idpf.org/2007/ops">'
        f'<head><meta charset="UTF-8"/><title>Navigation</title></head>'
        f'<body><nav epub:type="toc" id="toc"><ol>\n{nav_items}\n</ol></nav></body>'
        f'</html>'
    )

    # ── Build ZIP ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo('mimetype')
        info.compress_type = zipfile.ZIP_STORED
        zf.writestr(info, 'application/epub+zip')
        zf.writestr('META-INF/container.xml', container_xml)
        zf.writestr('OEBPS/content.opf', opf)
        zf.writestr('OEBPS/nav.xhtml', nav)
        zf.writestr('OEBPS/style.css', css)
        for pid, _, xhtml in pages:
            zf.writestr(f'OEBPS/{pid}.xhtml', xhtml)
    buf.seek(0)
    safe_home = ''.join(c for c in game.get('home_team', 'home')
                        if c.isalnum() or c in '-_')
    safe_away = ''.join(c for c in game.get('away_team', 'away')
                        if c.isalnum() or c in '-_')
    filename = f"lineup_{safe_home}_vs_{safe_away}_{device_key}.epub"
    return send_file(buf, mimetype='application/epub+zip',
                     as_attachment=True, download_name=filename)
