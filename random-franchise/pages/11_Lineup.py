import html
import streamlit as st
import streamlit.components.v1 as components
from ui.common import run_page, table


def render(repo, f):
    players = repo.list('players', f['id'])
    lineup = sorted(
        [p for p in players if p['area'] == 'lineup'],
        key=lambda p: (p.get('order', 99), p['name']),
    )
    rotation = sorted(
        [p for p in players if p['area'] == 'rotation'],
        key=lambda p: (p.get('order', 99), p['name']),
    )

    pitcher = None
    if rotation:
        choices = {p['id']: p for p in rotation}
        pitcher_id = st.selectbox(
            'Show starting pitcher',
            list(choices),
            format_func=lambda pid: choices[pid]['name'],
            key='lineup_pitcher:' + f['id'],
        )
        pitcher = choices[pitcher_id]

    st.caption(
        'Field positions follow Roster Manager. '
        'The pitcher selector changes this display only.'
    )

    positions = {
        'LF': (20, 19),
        'CF': (50, 10),
        'RF': (80, 19),
        'SS': (34, 40),
        '2B': (66, 40),
        '3B': (19, 58),
        '1B': (81, 58),
        'SP': (50, 60),
        'C': (50, 87),
        'DH': (83, 85),
    }

    field_players = list(lineup)
    if pitcher:
        field_players.append(pitcher)

    cards = []
    occupied = set()
    for p in field_players:
        position = 'SP' if pitcher and p['id'] == pitcher['id'] else p['position']
        if position not in positions:
            st.warning(p['name'] + ': no field slot for ' + position)
            continue
        if position in occupied:
            st.warning(
                'More than one player is assigned to ' + position
                + '. Check Roster Manager.'
            )
            continue
        occupied.add(position)
        x, y = positions[position]
        initials = ''.join(
            word[0] for word in p['name'].split()[:2]
        ).upper()
        order = (
            '#' + str(p['order']) + ' · '
            if p['kind'] == 'hitter' else ''
        )
        cards.append(
            f'<div class="player" style="left:{x}%;top:{y}%">'
            f'<div class="avatar">{html.escape(initials)}</div>'
            f'<div class="name">{html.escape(p["name"])}</div>'
            f'<div class="details">{order}{html.escape(position)}'
            f' · {p["ovr"]} OVR</div>'
            f'<div class="version">{html.escape(str(p["version"]))}</div>'
            '</div>'
        )

    components.html(
        '''
        <style>
        body {
            margin:0;
            font-family:Arial,sans-serif;
            color:white;
        }
        .field {
            position:relative;
            height:650px;
            overflow:hidden;
            background:#07121c;
            border:1px solid #476170;
            border-radius:24px;
            box-shadow:inset 0 0 90px #0009;
        }
        svg {
            position:absolute;
            width:100%;
            height:100%;
        }
        .player {
            position:absolute;
            transform:translate(-50%,-50%);
            width:170px;
            padding:12px 8px 10px;
            box-sizing:border-box;
            text-align:center;
            background:linear-gradient(145deg,#203448f5,#08111ef5);
            border:1px solid #7796aa;
            border-top:3px solid #f9c74f;
            border-radius:4px 18px 4px 18px;
            box-shadow:0 12px 25px #0008, inset 0 1px 0 #ffffff20;
            transition:transform .2s,box-shadow .2s;
        }
        .player:hover {
            transform:translate(-50%,-50%) scale(1.06);
            box-shadow:0 15px 30px #000a,0 0 20px #f9c74f40;
            z-index:5;
        }
        .avatar {
            margin:0 auto 8px;
            width:44px;
            height:44px;
            line-height:44px;
            border-radius:12px;
            background:linear-gradient(145deg,#356d93,#142c46);
            border:1px solid #9db8ca;
            font-size:18px;
            font-weight:bold;
            box-shadow:0 3px 10px #0006;
        }
        .name {
            font-size:14px;
            font-weight:800;
            text-shadow:0 2px 3px #000;
        }
        .details {
            display:inline-block;
            margin-top:7px;
            padding:4px 7px;
            border-radius:4px;
            background:#f9c74f;
            color:#101925;
            font-size:11px;
            font-weight:bold;
        }
        .version {
            margin-top:6px;
            color:#bfd2e0;
            font-size:10px;
            letter-spacing:1px;
            text-transform:uppercase;
        }
        @media(max-width:600px) {
            .player { width:100px; padding:7px 4px; }
            .avatar {
                width:30px; height:30px;
                line-height:30px; font-size:13px;
            }
            .name { font-size:11px; }
            .details,.version { font-size:9px; letter-spacing:0; }
        }
        @media(prefers-reduced-motion:reduce) {
            .player { transition:none; }
        }
        </style>
        <div class="field">
        <svg viewBox="0 0 1000 700" preserveAspectRatio="none">
            <defs>
                <radialGradient id="stadium">
                    <stop offset="0" stop-color="#284453"/>
                    <stop offset="1" stop-color="#06101b"/>
                </radialGradient>
                <radialGradient id="turf">
                    <stop offset="0" stop-color="#4aab6b"/>
                    <stop offset="1" stop-color="#174b38"/>
                </radialGradient>
                <linearGradient id="dirt" x2="0" y2="1">
                    <stop stop-color="#ce9c6c"/>
                    <stop offset="1" stop-color="#95613d"/>
                </linearGradient>
                <pattern id="mowing" width="100" height="100"
                         patternUnits="userSpaceOnUse"
                         patternTransform="rotate(35)">
                    <rect width="50" height="100" fill="#ffffff"
                          opacity=".055"/>
                    <rect x="50" width="50" height="100"
                          fill="#000000" opacity=".045"/>
                </pattern>
                <pattern id="seats" width="20" height="16"
                         patternUnits="userSpaceOnUse">
                    <rect x="3" y="3" width="12" height="6"
                          rx="2" fill="#547488" opacity=".4"/>
                </pattern>
                <clipPath id="playing-field">
                    <path d="M500 640 L60 235 Q500 -160 940 235 Z"/>
                </clipPath>
                <radialGradient id="light">
                    <stop stop-color="#e7f6ff" stop-opacity=".3"/>
                    <stop offset="1" stop-color="#e7f6ff"
                          stop-opacity="0"/>
                </radialGradient>
            </defs>

            <rect width="1000" height="700" fill="url(#stadium)"/>
            <path d="M0 210 Q500 -200 1000 210"
                  fill="none" stroke="url(#seats)" stroke-width="160"/>
            <path d="M45 231 Q500 -173 955 231"
                  fill="none" stroke="#8094a0" stroke-width="8"/>
            <path d="M60 235 Q500 -160 940 235"
                  fill="none" stroke="#ddbe68" stroke-width="3"/>

            <g clip-path="url(#playing-field)">
                <rect width="1000" height="700" fill="url(#turf)"/>
                <rect width="1000" height="700" fill="url(#mowing)"/>
            </g>

            <path d="M500 610 L240 420 L500 235 L760 420 Z"
                  fill="url(#dirt)"/>
            <path d="M500 555 L315 420 L500 287 L685 420 Z"
                  fill="url(#turf)"/>
            <path d="M500 555 L315 420 L500 287 L685 420 Z"
                  fill="url(#mowing)"/>

            <path d="M500 640 L60 235 M500 640 L940 235"
                  fill="none" stroke="#fff3dc" stroke-width="3"/>
            <circle cx="500" cy="440" r="24" fill="url(#dirt)"/>
            <rect x="492" y="434" width="16" height="5" fill="#fff3dc"/>
            <circle cx="500" cy="630" r="39" fill="url(#dirt)"/>

            <g fill="#fff3dc">
                <rect x="490" y="228" width="20" height="20"
                      transform="rotate(45 500 238)"/>
                <rect x="750" y="410" width="20" height="20"
                      transform="rotate(45 760 420)"/>
                <rect x="230" y="410" width="20" height="20"
                      transform="rotate(45 240 420)"/>
                <path d="M490 625 L510 625 L510 635 L500 645 L490 635 Z"/>
            </g>

            <ellipse cx="80" cy="70" rx="300" ry="220"
                     fill="url(#light)"/>
            <ellipse cx="920" cy="70" rx="300" ry="220"
                     fill="url(#light)"/>
            <text x="35" y="665" fill="#aec3ce" font-size="13"
                  letter-spacing="4">STARTING NINE</text>
        </svg>
        '''
        + ''.join(cards)
        + '</div>',
        height=670,
    )

    for area, title in [
        ('bench', 'Bench'),
        ('rotation', 'Starting rotation'),
        ('bullpen', 'Bullpen'),
    ]:
        st.subheader(title)
        table([
            {
                'Player': p['name'],
                'Position': p['position'],
                'OVR': p['ovr'],
                'Card': p['version'],
            }
            for p in sorted(
                players, key=lambda item: (item.get('order', 99), item['name'])
            )
            if p['area'] == area
        ])

    st.page_link(
        'pages/2_Roster_Manager.py',
        label='Edit roster and batting order',
        icon='✏️',
    )


run_page('Lineup', render, obs=False)
