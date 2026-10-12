import html
import base64
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit
import math

import streamlit as st
import streamlit.components.v1 as components

from services.wheel_engine import (
    current_job,
    available,
    spin,
    continue_spin,
    retry_impossible_branch,
)
from services.franchise_service import settings
from ui.common import navigate


COLD_BAT_EFFECTS = {
    'cold_bat_hot_seat',
    'cold_bat_order',
    'cold_bat_bench',
    'downgrade',
}


def text_key(value):
    text = unicodedata.normalize('NFKD', str(value or '').casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+', text))


def card_url(player):
    exact = {
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

    legacy = {
        ('manny ramirez', 94):
            'f5e8e6d59d01a65fa1a76fe3bc41d753',
        ('carlos beltran', 92):
            'ae298137b980fa4713aa235891188659',
        ('luis lara', 96):
            'b85163e6c27ffebaab0cfa52e6deb84d',
        ('daniel schneemann', 90):
            'c4b6a635bc56b98c94d77a9188b2087b',
        ('ozzie albies', 89):
            '3b1a482628a2a10f81bb6e47b9ee4e2d',
        ('chase headley', 88):
            '0725dd19ed80c6cff262389a69fa379e',
        ('chase utley', 88):
            '16588688df24c071adf191b89717de13',
        ('cam schlittler', 98):
            'ebb513f936b81fb5910c21d7687cbcad',
        ('anthony seigler', 67):
            '3675fe0474e7202d802666cb405a3ffa',
        ('junior caminero', 87):
            '5f74a86f361c5124d1ef06cbabad638e',
        ('freddie freeman', 83):
            'b304748509db213a30a08c2c0b3eba5b',
        ('clay buchholz', 83):
            '327387c1d18a25be5d41b963101818ff',
        ('clay bucholz', 83):
            '327387c1d18a25be5d41b963101818ff',
    }

    name = text_key(player.get('name'))
    overall = player.get('ovr')

    identifier = (
        exact.get((name, overall, text_key(player.get('series'))))
        or exact.get((name, overall, text_key(player.get('version'))))
        or legacy.get((name, overall))
    )

    if identifier:
        return (
            f'https://cards.theshow.com/mlb26/'
            f'{identifier}-baked-lg.webp'
        )

    saved_url = str(player.get('card_image_url') or '').strip()
    parsed = urlsplit(saved_url)

    if parsed.scheme == 'https' and parsed.netloc:
        return saved_url

    saved_id = str(player.get('card_uuid') or '').strip()

    if re.fullmatch(r'[a-fA-F0-9]{32}', saved_id):
        return (
            f'https://cards.theshow.com/mlb26/'
            f'{saved_id}-baked-lg.webp'
        )

    return None


def stadium_url():
    path = (
        Path(__file__).resolve().parents[1]
        / 'assets'
        / 'stadium_background.png'
    )

    if path.is_file():
        return (
            'data:image/png;base64,'
            + base64.b64encode(path.read_bytes()).decode('ascii')
        )

    return ''


def room_header(title, subtitle):
    background = stadium_url()

    st.markdown(
        '<div style="border:1px solid #744639;'
        'border-top:4px solid #ff334f;'
        'border-radius:14px;padding:26px 28px;'
        'margin-bottom:18px;background-color:#171b26;'
        'background-image:linear-gradient(90deg,'
        'rgba(9,13,22,.93),rgba(9,13,22,.3)),url(&quot;'
        + background
        + '&quot;);background-size:cover;'
        'background-position:center;">'
        '<div style="color:#f3cc78;font-size:11px;'
        'font-weight:800;letter-spacing:3px;">'
        'FRONT OFFICE • WHEEL ROOM</div>'
        '<div style="color:#fff0ce;font-size:32px;'
        'font-weight:900;margin:9px 0;">'
        + html.escape(title)
        + '</div>'
        '<div style="color:#d3d9e5;font-size:13px;">'
        + html.escape(subtitle)
        + '</div></div>',
        unsafe_allow_html=True,
    )


def result_summary(outcome):
    if outcome.get('follow_up'):
        return (
            'Continue to the follow-up wheel. '
            'Earlier restrictions carry forward.'
        )

    effect = outcome.get('effect', 'acquire')

    summaries = {
        'mvp_upgrade': (
            'Upgrade this MVP to their next higher-rated Event-legal '
            'card. No available upgrade: temporary protection.'
        ),
        'downgrade': (
            'Use this hitter’s next lower-rated Event-legal card. '
            'No available downgrade: Hot Seat Next Week.'
        ),
        'cold_bat_hot_seat': (
            'This hitter goes on the hot seat for the next week. '
            'Resolve between weeks.'
        ),
        'cold_bat_order': (
            'Start next week with this hitter batting 7th, 8th, or 9th. '
            'Arrange and confirm between weeks.'
        ),
        'cold_bat_bench': (
            'Start next week with this hitter on the bench. '
            'Arrange and confirm between weeks.'
        ),
        'reunion': (
            'Bring back this exact former card during offseason. '
            'Preserve the existing entry and stats.'
        ),
        'dfa': (
            'Move the selected player to DFA during offseason.'
        ),
        'demote': (
            'Move the selected player to Minors during offseason.'
        ),
        'trade': (
            'Continue to the incoming market wheel, '
            'then the position wheel.'
        ),
        'trade_market': (
            'Continue to the incoming position wheel.'
        ),
        'trade_position': (
            'Bank the completed trade and resolve it during offseason.'
        ),
        'challenge': (
            'Continue to create the assigned challenge. '
            'Saved game stats track quantitative goals.'
        ),
        'protect': (
            'Continue to apply protection or bank it, '
            'following the instructions below.'
        ),
        'unprotect': (
            'Continue to remove the selected player’s '
            'temporary protection.'
        ),
        'hot_seat': (
            'Continue to mark this player for Hot Seat targeting. '
            'This does not remove them.'
        ),
        'tag': (
            'Continue to grant the Franchise Tag '
            'or bank a tag-cap decision.'
        ),
        'extra_spin': (
            'Continue to queue the additional wheel spin(s).'
        ),
        'arrangement': (
            'Apply the arrangement in Roster Manager, '
            'then confirm below.'
        ),
        'deferred': (
            'No eligible outcome was available. '
            'Continue to record the unavailable branch.'
        ),
        'none': (
            'No roster change or reward applies to this outcome.'
        ),
    }

    if effect == 'acquire':
        return (
            f"Add {outcome.get('quantity', 1)} Event-legal card(s) "
            'matching this result during offseason. '
            'You choose the incoming card.'
        )

    return summaries.get(
        effect,
        'Continue to bank this result, then follow '
        'its instructions in Banked Moves.',
    )


def show_reveal(repo, result, read_only=False):
    outcome = result['result']
    effect = outcome.get('effect', 'acquire')

    consequence = effect in COLD_BAT_EFFECTS | {
        'dfa',
        'demote',
        'unprotect',
        'hot_seat',
    }

    neutral = bool(outcome.get('follow_up')) or effect in {
        'none',
        'deferred',
        'trade_market',
        'trade_position',
        'arrangement',
    }

    label = (
        'CONSEQUENCE'
        if consequence
        else 'NEXT STEP'
        if neutral
        else 'REWARD'
    )

    accent = (
        '#ff6375'
        if consequence
        else '#93b9e6'
        if neutral
        else '#efc778'
    )

    icon = '❄️' if consequence else '🎡' if neutral else '🏆'

    player_effects = COLD_BAT_EFFECTS | {
        'mvp_upgrade',
        'upgrade',
        'reunion',
        'dfa',
        'demote',
        'trade',
        'protect',
        'unprotect',
        'hot_seat',
        'tag',
        'challenge',
        'call_up',
    }

    target = (
        repo.get('players', result['target'])
        if effect in player_effects and result.get('target')
        else None
    )

    art = '<div class="symbol">' + icon + '</div>'
    target_text = ''

    if target:
        initials = ''.join(
            word[0] for word in target['name'].split()[:2]
        ).upper()

        art = (
            '<div class="card-fallback">'
            + html.escape(initials)
            + '</div>'
        )

        url = card_url(target)

        if url:
            art += (
                '<img src="'
                + html.escape(url, quote=True)
                + '" alt="'
                + html.escape(target['name'], quote=True)
                + '" onerror="this.style.display=\'none\'">'
            )

        role = (
            'Outgoing player'
            if effect == 'trade'
            else 'Returning player'
            if effect == 'reunion'
            else 'Selected player'
        )

        target_text = (
            '<div class="target">'
            + html.escape(role + ': ' + target['name'])
            + '</div>'
        )

        metadata = (
            str(target['ovr'])
            + ' OVR · '
            + str(
                target.get('series')
                or target.get('version')
                or 'Card'
            )
        )

        target_text += (
            '<div class="metadata">'
            + html.escape(metadata)
            + '</div>'
        )

    options = result.get('available', [])
    total = math.fsum(
        float(wedge.get('weight', 1))
        for wedge in options
    )

    selected = next(
        (
            wedge for wedge in options
            if wedge['id'] == outcome['id']
        ),
        None,
    )

    chance = ''

    if selected and total > 0:
        chance = (
            f"{float(selected.get('weight', 1)) / total * 100:.2f}% "
            'of eligible spin weight'
        )

    footer = (
        'LATEST SAVED RESULT • VIEW ONLY'
        if read_only
        else 'RESULT SAVED • CONTINUE BELOW'
    )

    css = '''
    <style>
    body {
        margin: 0;
        font-family: Arial, sans-serif;
        color: #f5f2e9;
    }

    .reveal {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        padding: 24px;
        min-height: 260px;
        box-sizing: border-box;
        border: 1px solid ACCENT;
        border-top: 4px solid ACCENT;
        border-radius: 14px;
        background:
            radial-gradient(
                ellipse at right,
                #8e243333,
                transparent 65%
            ),
            linear-gradient(135deg, #22202b, #0c121c);
    }

    .copy {
        flex: 1;
        min-width: 0;
    }

    .eyebrow {
        font-size: 11px;
        letter-spacing: 3px;
        font-weight: bold;
        color: ACCENT;
    }

    h2 {
        font-size: 32px;
        line-height: 1.15;
        margin: 12px 0;
        color: ACCENT;
        overflow-wrap: anywhere;
    }

    .target {
        font-size: 17px;
        font-weight: bold;
        margin-top: 14px;
    }

    .metadata,
    .chance {
        font-size: 11px;
        color: #bcc7d8;
        margin-top: 7px;
    }

    .summary {
        font-size: 13px;
        line-height: 1.6;
        margin-top: 16px;
        color: #eef0f5;
    }

    .footer {
        font-size: 10px;
        letter-spacing: 1px;
        color: ACCENT;
        margin-top: 18px;
    }

    .art {
        position: relative;
        flex: 0 0 130px;
        width: 130px;
        height: 184px;
        display: grid;
        place-items: center;
    }

    .art img {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: contain;
        filter: drop-shadow(0 7px 14px #0008);
    }

    .card-fallback {
        width: 115px;
        height: 155px;
        display: grid;
        place-items: center;
        border: 1px solid ACCENT;
        border-radius: 9px;
        font-size: 33px;
        color: ACCENT;
        background: #1d2433;
    }

    .symbol {
        font-size: 66px;
    }

    @media(max-width:600px) {
        .reveal {
            padding: 18px;
            gap: 12px;
        }

        h2 {
            font-size: 25px;
        }

        .art {
            flex-basis: 90px;
            width: 90px;
            height: 130px;
        }

        .card-fallback {
            width: 85px;
            height: 115px;
            font-size: 25px;
        }
    }
    </style>
    '''.replace('ACCENT', accent)

    body = (
        '<div class="reveal">'
        '<div class="copy">'
        '<div class="eyebrow">'
        + label
        + '</div><h2>'
        + html.escape(outcome['text'])
        + '</h2><div class="chance">'
        + chance
        + '</div>'
        + target_text
        + '<div class="summary">'
        + html.escape(result_summary(outcome))
        + '</div><div class="footer">'
        + footer
        + '</div></div><div class="art">'
        + art
        + '</div></div>'
    )

    components.html(css + body, height=350, scrolling=True)


def wheel_svg(options):
    """Draw weighted wedges and return their center angles."""
    colors = [
        '#d62845',
        '#edc16d',
        '#33577e',
        '#b64e32',
        '#70506e',
    ]

    weights = [
        float(option.get('weight', 1))
        for option in options
    ]
    total = math.fsum(weights)

    if total <= 0:
        return '', []

    pieces = []
    centers = []
    cursor = 0.0

    for index, weight in enumerate(weights):
        angle = weight / total * 360
        middle = cursor + angle / 2
        centers.append(middle)

        color = colors[index % len(colors)]
        label_color = (
            '#111827'
            if index % len(colors) == 1
            else '#fff2da'
        )

        if angle > 0:
            if math.isclose(angle, 360, abs_tol=1e-8):
                pieces.append(
                    f'<circle cx="180" cy="180" r="155" '
                    f'fill="{color}" stroke="#111827" '
                    'stroke-width="2"/>'
                )
            else:
                start = math.radians(cursor - 90)
                end = math.radians(cursor + angle - 90)

                x1 = 180 + 155 * math.cos(start)
                y1 = 180 + 155 * math.sin(start)
                x2 = 180 + 155 * math.cos(end)
                y2 = 180 + 155 * math.sin(end)

                pieces.append(
                    f'<path d="M180 180 L{x1} {y1} '
                    f'A155 155 0 {int(angle > 180)} '
                    f'1 {x2} {y2} Z" '
                    f'fill="{color}" stroke="#111827" '
                    'stroke-width="2"/>'
                )

            radians = math.radians(middle - 90)
            x = 180 + 112 * math.cos(radians)
            y = 180 + 112 * math.sin(radians)

            pieces.append(
                f'<text x="{x}" y="{y}" text-anchor="middle" '
                f'dominant-baseline="middle" fill="{label_color}" '
                'font-size="13" font-weight="bold">'
                f'{index + 1}</text>'
            )

        cursor += angle

    pieces.append(
        '<circle cx="180" cy="180" r="30" fill="#111827" '
        'stroke="white" stroke-width="2"/>'
    )

    return ''.join(pieces), centers


def visual(result, reduced):
    options = result.get('available', [])

    if not options:
        return

    pieces, centers = wheel_svg(options)

    if not centers:
        return

    selected = next(
        (
            index for index, wedge in enumerate(options)
            if wedge['id'] == result['result']['id']
        ),
        None,
    )

    if selected is None:
        return

    rotation = 1440 - centers[selected]

    animation = (
        ''
        if reduced
        else 'animation:land 3s cubic-bezier(.14,.62,.19,1) forwards;'
    )

    label = html.escape(result['result']['text'])

    components.html(
        f'''
        <style>
        body {{
            margin: 0;
            background: #0a1421;
            color: white;
            text-align: center;
            font-family: sans-serif;
        }}

        svg {{
            width: 340px;
            max-width: 100%;
            transform: rotate({rotation}deg);
            {animation}
        }}

        @keyframes land {{
            from {{
                transform: rotate(0deg);
            }}
            to {{
                transform: rotate({rotation}deg);
            }}
        }}

        @media(prefers-reduced-motion:reduce) {{
            svg {{
                animation: none!important;
            }}
        }}
        </style>

        <div style="font-size:28px;color:#ff334f;">▼</div>
        <svg viewBox="0 0 360 360">{pieces}</svg>
        <div>Selected wedge {selected + 1}: {label}</div>
        ''',
        height=420,
    )


def wheel_preview(options):
    if not options:
        return

    pieces, centers = wheel_svg(options)

    if not centers:
        return

    components.html(
        '<div style="text-align:center;color:white;'
        'font-family:sans-serif;">'
        '<div style="font-size:28px;color:#ff334f;">▼</div>'
        '<svg viewBox="0 0 360 360" '
        'style="width:100%;max-width:340px;">'
        + pieces
        + '</svg></div>',
        height=410,
    )

    st.caption(
        'Wedge numbers match the list below. '
        'Wedge sizes reflect the eligible outcomes’ weights.'
    )


def selected_player_details(target):
    if not target:
        st.warning('The selected player is unavailable.')
        return

    st.write('**Selected player:** ' + target['name'])

    st.write(
        '**Card:** '
        + str(target.get('ovr', ''))
        + ' OVR · '
        + str(target.get('version') or 'Not recorded')
    )


def banked_timing():
    st.write('**Timing:** Apply during offseason in Banked Moves.')

    st.caption(
        'Click Continue with this result to bank it. '
        'Your roster does not change immediately.'
    )


def explain_result(repo, fid, job, result):
    outcome = result['result']
    effect = outcome.get('effect', 'acquire')

    target = (
        repo.get('players', result['target'])
        if result.get('target')
        else None
    )

    follow = outcome.get('follow_up')

    with st.container(border=True):
        st.subheader('What this means')

        if follow:
            st.write(
                '**Next step:** Continue to another wheel. '
                'This result’s restrictions carry into that spin.'
            )

            if outcome.get('description'):
                st.write('**Instructions:** ' + outcome['description'])

            return

        if effect == 'mvp_upgrade':
            selected_player_details(target)

            st.write(
                '**Reward:** Upgrade the Weekly MVP to their next '
                'available higher-rated Event-legal card.'
            )

            st.write(
                '**Player choice:** This reward belongs to the selected '
                'MVP. It cannot be transferred to a teammate.'
            )

            st.write(
                '**If no upgrade exists:** Confirm that no higher-rated '
                'Event-legal version is available, then resolve the '
                'reward as temporary protection instead.'
            )

            st.write(
                '**Roster and stats:** The upgrade updates the existing '
                'player entry and preserves its saved stats.'
            )

            banked_timing()
            return

        if effect in COLD_BAT_EFFECTS:
            selected_player_details(target)

            st.write(
                '**Player choice:** This consequence applies to '
                'the hitter selected during Cold Bat review.'
            )

            if effect == 'cold_bat_hot_seat':
                st.write(
                    '**Consequence:** Put this hitter on the hot seat '
                    'for the next week.'
                )

                st.write(
                    '**Roster:** The player remains on your roster. '
                    'Hot Seat targeting does not automatically remove them.'
                )

            elif effect == 'cold_bat_order':
                st.write(
                    '**Consequence:** Start the next week with this '
                    'hitter batting 7th, 8th, or 9th.'
                )

                st.write(
                    '**How to apply:** Arrange the batting order in '
                    'Roster Manager, then resolve this consequence '
                    'in Banked Moves.'
                )

                st.caption(
                    'Keep that arrangement through validation and '
                    'the start of the next week.'
                )

                navigate('Arrange batting order', 'Roster Manager')

            elif effect == 'cold_bat_bench':
                st.write(
                    '**Consequence:** Start the next week with this '
                    'hitter on the bench.'
                )

                st.write(
                    '**How to apply:** Move the hitter to the bench '
                    'in Roster Manager and fill their lineup position. '
                    'Then resolve this consequence in Banked Moves.'
                )

                st.caption(
                    'Keep that arrangement through validation and '
                    'the start of the next week.'
                )

                navigate('Arrange lineup and bench', 'Roster Manager')

            else:
                st.write(
                    '**Consequence:** Replace this hitter’s card with '
                    'their next available lower-rated Event-legal version.'
                )

                st.write(
                    '**Restriction:** Keep the same player. '
                    'You cannot substitute a different hitter.'
                )

                st.write(
                    '**If no downgrade exists:** Confirm that no '
                    'lower-rated legal version is available. '
                    'The consequence becomes Hot Seat Next Week.'
                )

                st.write(
                    '**Stats:** Updating the existing player entry '
                    'preserves its saved stats.'
                )

            banked_timing()
            return

        if effect == 'reunion':
            st.write(
                '**Reward:** Bring back one randomly selected '
                'Event-eligible card from a previous season.'
            )

            selected_player_details(target)

            if target:
                st.write(
                    '**Card series:** '
                    + (target.get('series') or 'Not recorded')
                )

            st.write(
                '**Player choice:** The wheel selected the exact former '
                'card. You cannot substitute another player or version.'
            )

            st.write(
                '**Stats:** Reuse the existing player entry and '
                'preserve its saved stats.'
            )

            st.write(
                '**Roster:** Resolve the reward in Banked Moves. '
                'An inactive card returns to Minors, then you can '
                'arrange it in Roster Manager.'
            )

            st.write(
                '**Eligibility:** The card must still meet the current '
                'Event rules when you resolve the reward.'
            )

            banked_timing()
            return

        if effect in ['trade', 'trade_market', 'trade_position']:
            context = job.get('trade_context', {})

            if effect == 'trade':
                if target:
                    st.write('**Outgoing player:** ' + target['name'])

                st.write(
                    '**Next:** Continue to spin the incoming player’s '
                    'team, division, or league, then their position.'
                )

                st.caption(
                    'The trade is banked after both additional spins. '
                    'Your roster does not change yet.'
                )

            elif effect == 'trade_market':
                st.write('**Incoming market:** ' + outcome['text'])

                st.write(
                    '**Allowed teams:** '
                    + ', '.join(outcome.get('teams', []))
                )

                st.write(
                    '**Next:** Continue to spin the incoming position.'
                )

            else:
                st.write(
                    '**Incoming market:** '
                    + context.get('market_label', '')
                )

                st.write('**Position result:** ' + outcome['text'])

                st.write(
                    '**Allowed primary or secondary positions:** '
                    + ', '.join(outcome.get('positions', []))
                )

                st.write(
                    '**Next:** Continue to bank the complete trade. '
                    'Apply it during offseason in Banked Moves.'
                )

            st.write(
                '**Player type:** Hitter for hitter; pitcher for pitcher. '
                'The incoming card must be Event-eligible.'
            )

            if context.get('max_ovr') is not None:
                st.write(
                    '**Maximum incoming OVR:** '
                    + str(context['max_ovr'])
                )

            return

        if effect in ['acquire', 'dfa', 'demote']:
            if effect == 'acquire':
                quantity = outcome.get('quantity', 1)

                st.write(
                    f'**Reward:** Add {quantity} Event-eligible '
                    'card(s) matching this wheel result.'
                )

                st.write(
                    '**Player choice:** Choose the incoming card yourself. '
                    'The displayed target does not apply to this reward.'
                )

                st.write(
                    '**Roster:** Your previous starter can stay on '
                    'the bench if roster limits allow.'
                )

            else:
                instruction = {
                    'dfa': 'Move the selected player to DFA.',
                    'demote': 'Move the selected player to Minors.',
                }[effect]

                st.write('**Required action:** ' + instruction)
                selected_player_details(target)

            st.write(
                '**Result instructions:** '
                + outcome.get('description', outcome['text'])
            )

            branch = result.get('job', {}).get('constraints', [])

            if branch:
                st.write(
                    '**Earlier wheel restrictions:** '
                    + ' → '.join(branch)
                )

            banked_timing()
            return

        if effect == 'challenge':
            st.write('**Challenge:** ' + outcome['text'])

            scopes = {
                'next_game': 'Your next qualifying saved game.',
                'next_run': 'Your entire next week.',
                'run': 'This week.',
            }

            scope = outcome.get('scope', 'next_game')

            st.write(
                '**When it counts:** '
                + scopes.get(scope, 'See the challenge instructions.')
            )

            if outcome.get('metric'):
                st.write(
                    '**Goal:** '
                    + str(outcome.get('threshold', 1))
                    + ' '
                    + outcome['metric'].upper()
                )

                st.caption('Progress updates from saved game stats.')

            else:
                st.caption(
                    'Provide evidence and confirm this challenge '
                    'manually during offseason.'
                )

            rewards = {
                'tag': 'Franchise Tag',
                'protection': 'Player protection',
                'upgrade': 'Card upgrade',
            }

            reward = outcome.get('reward', 'protection')
            st.write('**Reward:** ' + rewards.get(reward, reward))

        elif effect == 'protect':
            if 'Next Run' in outcome['text']:
                st.write(
                    '**Reward:** Protection for next week. Continue '
                    'to bank it, then apply it during offseason.'
                )
            else:
                st.write(
                    '**Reward:** Give the selected player temporary '
                    'protection from removal when you continue.'
                )

        elif effect == 'unprotect':
            st.write(
                '**Consequence:** Remove the selected player’s '
                'temporary protection when you continue.'
            )

        elif effect == 'hot_seat':
            st.write(
                '**Consequence:** Mark the selected player for '
                'Hot Seat targeting when you continue. '
                'This does not remove them.'
            )

        elif effect == 'tag':
            st.write(
                '**Reward:** Grant the selected player a Franchise Tag '
                'when you continue. If the tag cap is full, resolve '
                'the replacement decision in Banked Moves.'
            )

        elif effect == 'extra_spin':
            st.write(
                '**Reward:** Add '
                + str(outcome.get('quantity', 1))
                + ' extra spin(s) on this wheel when you continue.'
            )

        elif effect == 'arrangement':
            st.write(
                '**Required action:** Apply the arrangement in '
                'Roster Manager, then check the confirmation below.'
            )

        elif effect == 'none':
            st.write('No roster change or reward is applied.')

        elif effect == 'deferred':
            st.write(
                'No eligible result was available. Continue to defer '
                'this branch, or use the retry button if available.'
            )

        else:
            banked_timing()

        if target:
            st.write('**Selected player:** ' + target['name'])

        if outcome.get('description'):
            st.write('**Instructions:** ' + outcome['description'])


def render(repo, f):
    fid = f['id']
    job = current_job(repo, fid)

    if not job:
        room_header(
            'Front Office Lounge',
            'Your next required spin will appear here.',
        )

        st.info('No wheel is due right now.')
        navigate('Return to Dashboard', 'Dashboard')

        saved = repo.list('spins', fid)

        if saved:
            st.subheader('Latest saved result')
            show_reveal(repo, saved[-1], read_only=True)

            st.caption(
                'This is a display of an existing result. '
                'No spin or reward is created.'
            )

        return

    special_names = {
        'trade_market': 'Trade Market — Team, Division, or League',
        'trade_position': 'Trade Position',
    }

    if job['wheel_id'] in special_names:
        title = special_names[job['wheel_id']]
    else:
        wheel = repo.get('wheels', f"{fid}:{job['wheel_id']}")

        if not wheel:
            st.error('Wheel configuration missing.')
            return

        title = wheel['display_name']

    room_header(
        title,
        'Your required spin • Every saved result stays in franchise history',
    )

    if job.get('constraints'):
        st.info(
            'Earlier restrictions: '
            + ' → '.join(job['constraints'])
        )

    cfg = settings(repo, fid)

    reduced = st.checkbox(
        'Reduced motion — show a static wheel',
        value=cfg.get('reduced_motion', False),
        key='wheel_reduced_motion:' + fid,
    )

    result = repo.get('spins', job['id'])

    if not result:
        options = available(repo, fid, job)
        wheel_preview(options)

        total = math.fsum(
            float(wedge.get('weight', 1))
            for wedge in options
        )

        with st.expander('Eligible wedges, weights, and chances'):
            st.dataframe(
                [
                    {
                        'Number': index + 1,
                        'Wedge': wedge['text'],
                        'Weight': wedge.get('weight', 1),
                        'Chance': (
                            f"{float(wedge.get('weight', 1)) / total * 100:.2f}%"
                            if total > 0
                            else '0%'
                        ),
                    }
                    for index, wedge in enumerate(options)
                ],
                hide_index=True,
            )

            st.caption(
                'These chances use the outcomes eligible for this spin.'
            )

        if not options:
            st.info(
                'No eligible wedges are available. Record an '
                'unavailable branch result to continue.'
            )

        if st.button(
            '🎡 SPIN REQUIRED WHEEL',
            type='primary',
            use_container_width=True,
            key='spin:' + job['id'],
        ):
            spin(repo, fid, job['id'])
            st.rerun()

    else:
        visual(result, reduced)
        show_reveal(repo, result)

        with st.expander('Full result instructions', expanded=True):
            explain_result(repo, fid, job, result)

        acknowledged = False

        if result['result'].get('effect') == 'arrangement':
            navigate(
                'Apply arrangement in Roster Manager',
                'Roster Manager',
            )

            acknowledged = st.checkbox(
                'I applied this arrangement using existing cards '
                'and verified it is legal.',
                key='arrangement_confirmation:' + job['id'],
            )

        if (
            result['result']['id'] == 'impossible'
            and job.get('parent_spin')
        ):
            if st.button(
                'Retry impossible child only (requires eligible options)',
                key='retry:' + job['id'],
            ):
                retry_impossible_branch(repo, fid, job['id'])
                st.rerun()

        if st.button(
            'CONTINUE WITH THIS RESULT',
            type='primary',
            use_container_width=True,
            key='continue:' + job['id'],
        ):
            continue_spin(repo, fid, job['id'], acknowledged)
            st.rerun()

        st.caption(
            'The result is saved before display. '
            'Refreshing does not grant another spin.'
        )
