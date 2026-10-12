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


COLD_BAT_EFFECTS = {
    'cold_bat_hot_seat',
    'cold_bat_order',
    'cold_bat_bench',
    'downgrade',
}


def wheel_svg(options):
    """Draw weighted wedges and return their center angles."""
    colors = ['#42e2ae', '#277da1', '#f9c74f', '#f9844a', '#9b5de5']
    weights = [float(option.get('weight', 1)) for option in options]
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

        if angle > 0:
            if math.isclose(angle, 360, abs_tol=1e-8):
                pieces.append(
                    f'<circle cx="180" cy="180" r="155" '
                    f'fill="{color}" stroke="#111827" stroke-width="2"/>'
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
                    f'A155 155 0 {int(angle > 180)} 1 {x2} {y2} Z" '
                    f'fill="{color}" stroke="#111827" stroke-width="2"/>'
                )

            radians = math.radians(middle - 90)
            x = 180 + 112 * math.cos(radians)
            y = 180 + 112 * math.sin(radians)
            pieces.append(
                f'<text x="{x}" y="{y}" text-anchor="middle" '
                'dominant-baseline="middle" fill="#07111e" '
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
            margin:0;
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
                    + ' ' + outcome['metric'].upper()
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

    if job['wheel_id'] == 'cold_bat':
        st.caption('Cold Bat consequence for your selected hitter.')
    elif job['wheel_id'] == 'mvp':
        st.caption('Weekly MVP reward.')
    else:
        st.caption('Source: ' + str(job['source']))

    if job.get('constraints'):
        st.info(
            'Branch constraints: ' + ' → '.join(job['constraints'])
        )

    cfg = settings(repo, fid)
    reduced = st.checkbox(
        'Reduced motion / simple fallback',
        value=cfg.get('reduced_motion', False),
        key='wheel_reduced_motion:' + fid,
    )

    result = repo.get('spins', job['id'])

    if not result:
        options = available(repo, fid, job)

        if not reduced:
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
                            if total > 0 else '0%'
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
                'No eligible wedges are available. '
                'Record an unavailable branch result to continue.'
            )

        if st.button(
            'Spin required wheel',
            type='primary',
            key='spin:' + job['id'],
        ):
            spin(repo, fid, job['id'])
            st.rerun()

    else:
        if not reduced:
            visual(result, reduced)

        st.success('Result: ' + result['result']['text'])
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
            'Continue with this result',
            type='primary',
            key='continue:' + job['id'],
        ):
            continue_spin(repo, fid, job['id'], acknowledged)
            st.rerun()

        st.caption(
            'The result is saved before display. '
            'Refreshing does not grant another spin.'
        )
