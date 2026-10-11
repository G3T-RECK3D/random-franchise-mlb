import html
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


def visual(result, reduced):
    options = result['available']
    if not options:
        return

    count = len(options)
    angle = 360 / count
    selected = next(
        (
            index for index, wedge in enumerate(options)
            if wedge['id'] == result['result']['id']
        ),
        0,
    )
    pieces = []
    colors = ['#42e2ae', '#277da1', '#f9c74f', '#f9844a', '#9b5de5']

    for index, wedge in enumerate(options):
        start = math.radians(index * angle - 90)
        end = math.radians((index + 1) * angle - 90)
        x1 = 180 + 155 * math.cos(start)
        y1 = 180 + 155 * math.sin(start)
        x2 = 180 + 155 * math.cos(end)
        y2 = 180 + 155 * math.sin(end)

        if count == 1:
            pieces.append(
                '<circle cx="180" cy="180" r="155" fill="#42e2ae"/>'
            )
        else:
            pieces.append(
                f'<path d="M180 180 L{x1} {y1} '
                f'A155 155 0 {int(angle > 180)} 1 {x2} {y2} Z" '
                f'fill="{colors[index % len(colors)]}" '
                'stroke="#0a1421"/>'
            )

        middle = math.radians((index + 0.5) * angle - 90)
        x = 180 + 110 * math.cos(middle)
        y = 180 + 110 * math.sin(middle)
        pieces.append(
            f'<text x="{x}" y="{y}" fill="#07111e" '
            'text-anchor="middle" font-size="12">'
            f'{index + 1}</text>'
        )

    rotation = -(selected + 0.5) * angle + 1440
    animation = (
        ''
        if reduced
        else 'animation:land 3s cubic-bezier(.14,.62,.19,1) forwards;'
    )
    svg = ''.join(pieces)
    label = html.escape(result['result']['text'])

    components.html(
        f'''
        <style>
        body {{
            background:#0a1421;
            color:white;
            text-align:center;
            font-family:sans-serif;
        }}
        svg {{
            width:340px;
            max-width:100%;
            transform:rotate({rotation}deg);
            {animation}
        }}
        @keyframes land {{
            from {{ transform:rotate(0deg); }}
            to {{ transform:rotate({rotation}deg); }}
        }}
        @media(prefers-reduced-motion:reduce) {{
            svg {{ animation:none!important; }}
        }}
        </style>
        <div style="font-size:28px">▼</div>
        <svg viewBox="0 0 360 360">{svg}</svg>
        <div>Selected wedge {selected + 1}: {label}</div>
        ''',
        height=420,
    )


def wheel_preview(options):
    if not options:
        return

    colors = ['#ff334f', '#ffb703', '#34d399', '#60a5fa', '#a78bfa']
    angle = 360 / len(options)
    pieces = []

    for index, option in enumerate(options):
        color = colors[index % len(colors)]
        start = math.radians(index * angle - 90)
        end = math.radians((index + 1) * angle - 90)
        x1 = 180 + 155 * math.cos(start)
        y1 = 180 + 155 * math.sin(start)
        x2 = 180 + 155 * math.cos(end)
        y2 = 180 + 155 * math.sin(end)

        if len(options) == 1:
            pieces.append(
                f'<circle cx="180" cy="180" r="155" fill="{color}"/>'
            )
        else:
            pieces.append(
                f'<path d="M180 180 L{x1} {y1} '
                f'A155 155 0 {int(angle > 180)} 1 {x2} {y2} Z" '
                f'fill="{color}" stroke="#111827" stroke-width="3"/>'
            )

        middle = math.radians((index + 0.5) * angle - 90)
        x = 180 + 110 * math.cos(middle)
        y = 180 + 110 * math.sin(middle)
        pieces.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" '
            'fill="#111827" font-size="20" font-weight="bold">'
            f'{index + 1}</text>'
        )

    components.html(
        '<div style="text-align:center;color:white;'
        'font-family:sans-serif;">'
        '<div style="font-size:28px;color:#ff334f;">▼</div>'
        '<svg viewBox="0 0 360 360" style="width:100%;max-width:340px;">'
        + ''.join(pieces)
        + '<circle cx="180" cy="180" r="34" fill="#111827" '
        'stroke="white" stroke-width="3"/>'
        '<text x="180" y="187" text-anchor="middle" '
        'fill="white" font-size="18" font-weight="bold">SPIN</text>'
        '</svg></div>',
        height=410,
    )
    st.caption(
        'Ready to spin. Wedge numbers match the list below; '
        'the configured weights determine the odds.'
    )


def explain_result(repo, fid, job, result):
    outcome = result['result']
    effect = outcome.get('effect', 'acquire')
    target = (
        repo.get('players', result['target'])
        if result.get('target') else None
    )
    follow = outcome.get('follow_up')

    with st.container(border=True):
        st.subheader('What this means')

        if follow:
            st.write(
                '**Next step:** Continue to another wheel. '
                'This result’s restrictions carry into that spin.'
            )

        elif effect == 'reunion':
            st.write(
                '**Reward:** Bring back one randomly selected '
                'Event-eligible card from a previous season.'
            )

            if target:
                st.write('**Returning player:** ' + target['name'])
                st.write('**Overall:** ' + str(target['ovr']))
                st.write(
                    '**Card series:** '
                    + (target.get('series') or 'Not recorded')
                )
                st.write(
                    '**Card version:** '
                    + (target.get('version') or 'Not recorded')
                )
            else:
                st.warning('The selected former card is unavailable.')

            st.write(
                '**Player choice:** The wheel has already selected '
                'the exact former card. You cannot replace it '
                'with another player or card version.'
            )
            st.write(
                '**Stats:** The existing player entry and its saved '
                'stats are preserved. A duplicate is not created.'
            )
            st.write(
                '**Roster:** Resolve the reward in Banked Moves. '
                'An inactive card returns to Minors, then you can '
                'arrange it in Roster Manager.'
            )
            st.write(
                '**Timing:** During offseason. '
                'The card must still meet the current Event rules '
                'when you resolve the reward.'
            )
            st.caption(
                'Click Continue with this result to bank it. '
                'Your roster does not change immediately.'
            )

        elif effect in ['trade', 'trade_market', 'trade_position']:
            context = job.get('trade_context', {})

            if effect == 'trade':
                if target:
                    st.write('**Outgoing player:** ' + target['name'])
                st.write(
                    '**Next:** Continue to spin the incoming player’s '
                    'team, division, or league. Then spin their position.'
                )
                st.caption(
                    'The trade will be banked after both additional spins. '
                    'Your roster does not change yet.'
                )

            elif effect == 'trade_market':
                st.write('**Incoming market:** ' + outcome['text'])
                st.write(
                    '**Allowed teams:** ' + ', '.join(outcome['teams'])
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
                    '**Allowed primary positions:** '
                    + ', '.join(outcome['positions'])
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

        elif effect in ['acquire', 'dfa', 'demote']:
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
                    'demote': 'Move the selected player to minors.',
                }[effect]
                st.write('**Required action:** ' + instruction)
                if target:
                    st.write('**Selected player:** ' + target['name'])

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
            st.write('**Timing:** Apply during offseason in Banked Moves.')
            st.caption(
                'Click Continue with this result to bank it. '
                'This does not change your roster immediately.'
            )

        else:
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
                        + ' ' + outcome['metric'].upper()
                    )
                    st.caption('Progress updates from saved game stats.')
                else:
                    st.caption(
                        'This challenge requires evidence and manual '
                        'confirmation during offseason.'
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
                        'protection from removal. Applied when you continue.'
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
                    'the replacement decision in Banked Moves during offseason.'
                )

            elif effect == 'extra_spin':
                st.write(
                    '**Reward:** Add extra spin(s) on this wheel '
                    'when you continue.'
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
                st.write(
                    '**Timing:** Continue to bank this result. '
                    'Review and resolve it during offseason in Banked Moves.'
                )

        if effect not in [
            'reunion', 'trade', 'trade_market', 'trade_position',
            'acquire', 'dfa', 'demote',
        ]:
            if target and not follow:
                st.write('**Selected player:** ' + target['name'])
            if outcome.get('description'):
                st.write('**Instructions:** ' + outcome['description'])


def render(repo, f):
    fid = f['id']
    job = current_job(repo, fid)

    if not job:
        st.info('No wheel is due right now.')
        navigate('Next step on dashboard', 'Dashboard')
        return

    special_names = {
        'trade_market': 'Trade Market — Team, Division, or League',
        'trade_position': 'Trade Position',
    }
    if job['wheel_id'] in special_names:
        st.subheader(special_names[job['wheel_id']])
    else:
        wheel = repo.get('wheels', f"{fid}:{job['wheel_id']}")
        if not wheel:
            st.error('Wheel configuration missing.')
            return
        st.subheader(wheel['display_name'])

    st.caption('Source: ' + job['source'])
    if job.get('constraints'):
        st.info('Branch constraints: ' + ' → '.join(job['constraints']))

    cfg = settings(repo, fid)
    reduced = st.checkbox(
        'Reduced motion / simple fallback',
        value=cfg.get('reduced_motion', False),
    )
    st.checkbox(
        'Sound (placeholder; V1 has no audio)',
        value=False,
        disabled=True,
    )

    result = repo.get('spins', job['id'])
    if not result:
        options = available(repo, fid, job)

        if not reduced:
            wheel_preview(options)

        with st.expander('Eligible wedges and weights'):
            st.dataframe(
                [
                    {
                        'Number': index + 1,
                        'Wedge': wedge['text'],
                        'Weight': wedge.get('weight', 1),
                    }
                    for index, wedge in enumerate(options)
                ],
                hide_index=True,
            )

        if not options:
            st.info(
                'No eligible wedges are available. '
                'Continue by recording an unavailable branch result.'
            )

        if st.button('Spin required wheel', type='primary'):
            spin(repo, fid, job['id'])
            st.rerun()

    else:
        if not reduced:
            visual(result, reduced)

        st.success('Result: ' + result['result']['text'])
        explain_result(repo, fid, job, result)

        acknowledged = False
        if result['result'].get('effect') == 'arrangement':
            st.info(
                result['result'].get(
                    'description', result['result']['text'],
                )
            )
            navigate(
                'Apply arrangement in Roster Manager',
                'Roster Manager',
            )
            acknowledged = st.checkbox(
                'I applied this arrangement using existing cards '
                'and verified it is legal.'
            )

        if (
            result['result']['id'] == 'impossible'
            and job.get('parent_spin')
        ):
            if st.button(
                'Retry impossible child only (requires eligible options)'
            ):
                retry_impossible_branch(repo, fid, job['id'])
                st.rerun()

        if st.button('Continue with this result', type='primary'):
            continue_spin(repo, fid, job['id'], acknowledged)
            st.rerun()

        st.caption(
            'Result is persisted before display. '
            'Refreshing does not grant another spin.'
        )
