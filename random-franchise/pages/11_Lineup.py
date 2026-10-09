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
        body { margin:0; font-family:Arial,sans-serif; color:white; }
        .field {
            position:relative; height:650px; overflow:hidden;
            background:#102b23; border:1px solid #35594b;
            border-radius:20px;
        }
        svg { position:absolute; width:100%; height:100%; }
        .player {
            position:absolute; transform:translate(-50%,-50%);
            width:145px; padding:8px; box-sizing:border-box;
            text-align:center; background:rgba(9,19,32,.94);
            border:1px solid #5d7d8b; border-radius:12px;
            box-shadow:0 5px 15px #0005;
        }
        .avatar {
            margin:0 auto 5px; width:34px; height:34px;
            line-height:34px; border-radius:50%;
            background:#277da1; font-weight:bold;
        }
        .name { font-size:13px; font-weight:bold; }
        .details { margin-top:5px; color:#f9c74f; font-size:12px; }
        .version { margin-top:3px; color:#b7c8d4; font-size:11px; }
        @media(max-width:600px) {
            .player { width:100px; padding:5px; }
            .name { font-size:11px; }
            .details,.version { font-size:10px; }
        }
        </style>
        <div class="field">
        <svg viewBox="0 0 1000 700" preserveAspectRatio="none">
            <path d="M500 640 L60 235 Q500 -160 940 235 Z"
                  fill="#28754a"/>
            <path d="M500 610 L240 420 L500 235 L760 420 Z"
                  fill="#b77b4b"/>
            <path d="M500 560 L310 420 L500 285 L690 420 Z"
                  fill="#35985c"/>
            <path d="M500 640 L60 235 M500 640 L940 235"
                  fill="none" stroke="white" stroke-width="3"/>
            <circle cx="500" cy="440" r="24" fill="#b77b4b"/>
            <g fill="white">
                <rect x="490" y="228" width="20" height="20"/>
                <rect x="750" y="410" width="20" height="20"/>
                <rect x="230" y="410" width="20" height="20"/>
                <path d="M490 625 L510 625 L510 635 L500 645 L490 635 Z"/>
            </g>
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
