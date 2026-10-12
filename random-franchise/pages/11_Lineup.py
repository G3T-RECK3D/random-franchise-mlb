import html
import re
import unicodedata
from urllib.parse import urlsplit

import streamlit as st
import streamlit.components.v1 as components

from ui.common import run_page, table


def text_key(value):
    text = unicodedata.normalize(
        'NFKD', str(value or '').strip().casefold()
    )
    text = ''.join(
        character for character in text
        if not unicodedata.combining(character)
    )
    return ' '.join(re.findall(r'[a-z0-9]+', text))


CARD_ART = {
    ('lance berkman', 99, 'spotlight'):
        'f3ed2f8ef5616481987e95ce6cbb7e5c',
    ('mike trout', 99, 'awards'):
        'e84d5fa03896ff54cdadabf5d2ca8a7b',
    ('ozzie albies', 98, '2026 all star'):
        '6bca0765db76ea057be8289cf7bb0af2',
    ('max muncy', 92, 'cityscapes'):
        '5fe05e1065c026ec88edd48e841c80a7',
    ('dustin may', 99, 'new threads'):
        '0136a957b1243dcd640122b066a34aa7',
    ('adley rutschman', 99, 'new threads'):
        '095405569042bf08e28ca0c411eac121',
    ('jose ramirez', 95, 'mural'):
        '56c113bcf0449e4c45679da6a9f521de',
}

LEGACY_CARD_ART = {
    ('manny ramirez', 94): 'f5e8e6d59d01a65fa1a76fe3bc41d753',
    ('carlos beltran', 92): 'ae298137b980fa4713aa235891188659',
    ('luis lara', 96): 'b85163e6c27ffebaab0cfa52e6deb84d',
    ('daniel schneemann', 90): 'c4b6a635bc56b98c94d77a9188b2087b',
    ('ozzie albies', 89): '3b1a482628a2a10f81bb6e47b9ee4e2d',
    ('chase headley', 88): '0725dd19ed80c6cff262389a69fa379e',
    ('chase utley', 88): '16588688df24c071adf191b89717de13',
    ('cam schlittler', 98): 'ebb513f936b81fb5910c21d7687cbcad',
    ('anthony seigler', 67): '3675fe0474e7202d802666cb405a3ffa',
    ('junior caminero', 87): '5f74a86f361c5124d1ef06cbabad638e',
}


def card_avatar(player, initials):
    name = text_key(player.get('name'))
    try:
        overall = int(player.get('ovr', 0))
    except (TypeError, ValueError):
        overall = 0

    series = text_key(player.get('series'))
    version = text_key(player.get('version'))

    card_id = (
        CARD_ART.get((name, overall, series))
        or CARD_ART.get((name, overall, version))
        or LEGACY_CARD_ART.get((name, overall))
    )

    url = None

    if card_id:
        url = (
            f'https://cards.theshow.com/mlb26/'
            f'{card_id}-baked-lg.webp'
        )
    else:
        saved_url = player.get('card_image_url')
        if isinstance(saved_url, str):
            saved_url = saved_url.strip()
            parsed = urlsplit(saved_url)
            if parsed.scheme == 'https' and parsed.netloc:
                url = saved_url

        if not url:
            saved_id = player.get('card_uuid')
            if (
                isinstance(saved_id, str)
                and re.fullmatch(r'[a-fA-F0-9]{32}', saved_id.strip())
            ):
                url = (
                    'https://cards.theshow.com/mlb26/'
                    + saved_id.strip()
                    + '-baked-lg.webp'
                )

    if not url:
        return (
            '<div class="avatar">'
            + html.escape(initials)
            + '</div>'
        )

    return (
        '<div class="card-art">'
        f'<span>{html.escape(initials)}</span>'
        f'<img src="{html.escape(url, quote=True)}" '
        f'alt="{html.escape(player["name"], quote=True)}" '
        'decoding="async" '
        'onerror="this.style.display=\'none\'">'
        '</div>'
    )


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
        'CF': (50, 17),
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

    for player in field_players:
        position = (
            'SP'
            if pitcher and player['id'] == pitcher['id']
            else player['position']
        )

        if position not in positions:
            st.warning(
                player['name'] + ': no field slot for ' + position
            )
            continue

        if position in occupied:
            st.warning(
                'More than one player is assigned to '
                + position + '. Check Roster Manager.'
            )
            continue

        occupied.add(position)
        x, y = positions[position]

        initials = ''.join(
            word[0] for word in player['name'].split()[:2]
        ).upper()
        order = (
            '#' + str(player['order']) + ' · '
            if player['kind'] == 'hitter' else ''
        )
        primary = str(player.get('primary') or 'Unknown')
        series = str(player.get('series') or 'Series not entered')
        secondary = player.get('secondary') or []

        if position == 'DH' or position == primary:
            fit = 'primary'
        elif position in secondary:
            fit = 'secondary'
        else:
            fit = 'out-of-position'

        cards.append(
            f'<div class="player {fit}" '
            f'style="left:{x}%;top:{y}%">'
            + card_avatar(player, initials)
            + '<div class="player-info">'
            + '<div class="name">'
            + html.escape(player['name'])
            + '</div>'
            + '<div class="details">'
            + html.escape(order + primary)
            + ' · '
            + html.escape(str(player['ovr']))
            + ' OVR</div>'
            + '<div class="version">'
            + html.escape(series)
            + '</div></div></div>'
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
            display:flex;
            align-items:center;
            gap:10px;
            width:250px;
            padding:0;
            box-sizing:border-box;
            text-align:left;
            background:none;
            border:none;
            transition:transform .2s;
        }
        .player.primary {
            --position-glow:rgba(52,211,153,.35);
        }
        .player.secondary {
            --position-glow:rgba(250,204,21,.35);
        }
        .player.out-of-position {
            --position-glow:rgba(248,113,113,.35);
        }
        .player:hover {
            transform:translate(-50%,-50%) scale(1.06);
            z-index:5;
        }
        .avatar {
            flex:0 0 44px;
            width:44px;
            height:44px;
            line-height:44px;
            text-align:center;
            border-radius:12px;
            background:linear-gradient(145deg,#356d93,#142c46);
            border:1px solid #9db8ca;
            font-size:18px;
            font-weight:bold;
            box-shadow:0 3px 10px #0006;
        }
        .card-art {
            position:relative;
            flex:0 0 82px;
            width:82px;
            height:114px;
            display:grid;
            place-items:center;
            border-radius:5px;
            background:transparent;
            font-weight:bold;
            box-shadow:0 0 18px 3px var(--position-glow);
        }
        .card-art img {
            position:absolute;
            inset:0;
            width:100%;
            height:100%;
            object-fit:contain;
            border-radius:5px;
            background:transparent;
        }
        .player-info {
            flex:1;
            min-width:0;
        }
        .name {
            font-size:14px;
            font-weight:800;
            line-height:1.25;
            text-shadow:0 2px 4px #000,0 0 8px #000;
        }
        .details {
            display:inline-block;
            margin-top:6px;
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
            line-height:1.35;
            text-transform:uppercase;
            text-shadow:0 2px 4px #000,0 0 8px #000;
        }
        @media(max-width:600px) {
            .player {
                flex-direction:column;
                gap:5px;
                width:100px;
                text-align:center;
            }
            .card-art {
                flex:0 0 auto;
                width:48px;
                height:66px;
            }
            .avatar {
                flex:0 0 auto;
                width:30px;
                height:30px;
                line-height:30px;
                font-size:13px;
            }
            .name { font-size:11px; }
            .details,.version {
                font-size:9px;
                letter-spacing:0;
            }
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
            <rect x="492" y="434" width="16" height="5"
                  fill="#fff3dc"/>
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

    ordered_players = sorted(
        players,
        key=lambda player: (
            player.get('order', 99),
            player['name'],
        ),
    )

    for area, title in [
        ('bench', 'Bench'),
        ('rotation', 'Starting rotation'),
        ('bullpen', 'Bullpen'),
    ]:
        st.subheader(title)
        table([
            {
                'Player': player['name'],
                'Position': player['position'],
                'OVR': player['ovr'],
                'Card': player['version'],
            }
            for player in ordered_players
            if player['area'] == area
        ])

    st.page_link(
        'pages/2_Roster_Manager.py',
        label='Edit roster and batting order',
        icon='✏️',
    )


run_page('Lineup', render, obs=False)
