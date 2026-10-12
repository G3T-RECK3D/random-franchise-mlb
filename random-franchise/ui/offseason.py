import math

import streamlit as st

from models.domain import State
from services.offseason_service import (
    confirm_end,
    select_mvp,
    progress,
    finish_validation,
    cold_bat_enabled,
    eligible_cold_bat_candidates,
    decide_cold_bat,
)
from services.game_engine import start_run
from services.roster_validator import validate
from services.challenge_service import confirm_manual
from services.stat_engine import (
    weekly_mvp_candidates,
    role_performance,
)
from ui.common import navigate, table


def show_weekly_mvp(repo, fid, run):
    candidates = weekly_mvp_candidates(repo, fid, run['id'])

    st.subheader('🏆 Overall Weekly MVP')
    st.caption(
        'Hitters and pitchers share one custom contribution score. '
        'This is a house scoring system; the final choice is yours.'
    )

    rows = []
    for candidate in candidates:
        totals = candidate['totals']
        hitter = candidate['kind'] == 'hitter'

        rows.append({
            'Player': candidate['name'],
            'Role': 'Hitter' if hitter else 'Pitcher',
            'MVP Score': round(candidate['score'], 3),
            'PA': totals.get('pa', 0) if hitter else '',
            'H': totals.get('h', 0) if hitter else '',
            'HR': totals.get('hr', 0) if hitter else '',
            'RBI': totals.get('rbi', 0) if hitter else '',
            'OPS': (
                f"{totals.get('ops', 0):.3f}" if hitter else ''
            ),
            'IP': totals.get('ip', '') if not hitter else '',
            'K': totals.get('so', 0) if not hitter else '',
            'ER': totals.get('er', 0) if not hitter else '',
            'Hits allowed': totals.get('ha', 0) if not hitter else '',
            'Walks allowed': totals.get('bb', 0) if not hitter else '',
        })

    table(rows)

    if candidates:
        best_score = max(c['score'] for c in candidates)
        leaders = [
            c['name']
            for c in candidates
            if math.isclose(
                c['score'],
                best_score,
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
        ]
        st.info(
            'Score recommendation: '
            + ', '.join(leaders)
            + (' (tied).' if len(leaders) > 1 else '.')
        )
    else:
        st.info(
            'No qualifying saved stats are available. '
            'You can still choose the MVP yourself.'
        )

    with st.expander('How the shared MVP score works'):
        st.write(
            'Hitters: 0.50 × singles + 0.80 × doubles '
            '+ 1.10 × triples + 1.40 × home runs '
            '+ 0.30 × (walks + hit-by-pitch) '
            '− 0.25 × (at-bats − hits + sacrifice flies) '
            '+ 0.20 × steals − 0.30 × caught stealing.'
        )
        st.write(
            'Pitchers: (innings pitched × ⅔) − earned runs.'
        )
        st.caption(
            'The pitching formula uses a baseline of two earned runs '
            'per three innings. Saved innings remain actual innings. '
            'Batting-order expectations apply to Cold Bat review, '
            'rather than the MVP score.'
        )

    labels = {}
    for player_id in dict.fromkeys(run['roster_ids']):
        player = repo.get('players', player_id)
        if player and player.get('franchise_id') == fid:
            labels[player_id] = (
                player['name']
                + ' · '
                + str(player.get('ovr', ''))
                + ' OVR · '
                + str(player.get('version', ''))
            )

    if not labels:
        st.warning('No available players were found for this week.')
        return

    ranked_ids = [
        c['player_id']
        for c in candidates
        if c['player_id'] in labels
    ]
    choices = ranked_ids + [
        player_id
        for player_id in labels
        if player_id not in ranked_ids
    ]

    pid = st.selectbox(
        'Choose Weekly MVP',
        choices,
        format_func=labels.get,
        key='weekly_mvp:' + run['id'],
    )
    st.caption(
        'Weekly MVP receives temporary protection through '
        'this offseason’s elimination cycle.'
    )

    if st.button(
        'Confirm Weekly MVP and spin reward',
        type='primary',
        key='confirm_weekly_mvp:' + run['id'],
    ):
        select_mvp(repo, fid, pid)
        st.rerun()


def show_cold_bat_review(repo, fid, run):
    """Return True when this week's Cold Bat review is complete."""
    if not cold_bat_enabled(repo, fid):
        return True

    st.subheader('🥶 Cold Bat review')
    decision = run.get('cold_bat_decision')

    if decision:
        if decision.get('status') == 'skipped':
            st.success('Cold Bat punishment was skipped for this week.')
        else:
            player = repo.get(
                'players',
                decision.get('player_id'),
            )
            name = player['name'] if player else 'Selected hitter'
            st.info('Cold Bat selection: ' + name)

            if decision.get('result'):
                st.write('Wheel result: ' + str(decision['result']))

            st.caption(
                'Status: '
                + str(decision.get('status', 'Recorded'))
                .replace('_', ' ')
                .title()
            )

        if decision.get('reason'):
            st.write('Reason: ' + decision['reason'])

        return True

    performances = role_performance(repo, fid, run['id'])
    eligible = eligible_cold_bat_candidates(
        repo, fid, run['id']
    )
    eligible_by_id = {
        candidate['player_id']: candidate
        for candidate in eligible
    }

    st.caption(
        'Review performance against the hitter’s batting-order role. '
        'A strong week can still have an underperformer, '
        'but you can skip punishment when nobody deserves it.'
    )

    if performances:
        rows = []
        for performance in performances:
            rows.append({
                'Player': performance['name'],
                'Batting spots': ', '.join(
                    str(order) for order in performance['orders']
                ),
                'Lineup PA': performance['pa'],
                'OBP': f"{performance['obp']:.3f}",
                'Expected OBP': (
                    f"{performance['expected_obp']:.3f}"
                ),
                'SLG': f"{performance['slg']:.3f}",
                'Expected SLG': (
                    f"{performance['expected_slg']:.3f}"
                ),
                'Role score': round(
                    performance['role_score'], 1
                ),
                'Assessment': performance['assessment'],
                'Eligible for selection': (
                    'Yes'
                    if performance['player_id'] in eligible_by_id
                    else 'No'
                ),
            })

        table(rows)
    else:
        st.info(
            'No usable lineup-role statistics were found for this week.'
        )

    stats = repo.list('stats', fid, run['id'])
    approximate = (
        any(p.get('snapshot_pa', 0) for p in performances)
        or any(
            row.get('assignment_source') == 'start_snapshot'
            for row in stats
        )
    )
    if approximate:
        st.warning(
            'Some older games use the week’s starting lineup '
            'to estimate batting spots. Consider any lineup changes '
            'when making your decision.'
        )

    st.caption(
        'Only eligible, unprotected active hitters with at least '
        'five recorded lineup plate appearances and a role score '
        'below 90 can be selected. Weekly MVP protection applies.'
    )

    with st.expander('Batting-order expectations'):
        table([
            {
                'Spot': '1',
                'Expected OBP': '.400',
                'Expected SLG': '.500',
                'OBP weight': '65%',
                'SLG weight': '35%',
            },
            {
                'Spot': '2',
                'Expected OBP': '.400',
                'Expected SLG': '.600',
                'OBP weight': '50%',
                'SLG weight': '50%',
            },
            {
                'Spot': '3',
                'Expected OBP': '.380',
                'Expected SLG': '.650',
                'OBP weight': '45%',
                'SLG weight': '55%',
            },
            {
                'Spot': '4–5',
                'Expected OBP': '.360',
                'Expected SLG': '.700',
                'OBP weight': '35%',
                'SLG weight': '65%',
            },
            {
                'Spot': '6–7',
                'Expected OBP': '.340',
                'Expected SLG': '.550',
                'OBP weight': '45%',
                'SLG weight': '55%',
            },
            {
                'Spot': '8–9',
                'Expected OBP': '.320',
                'Expected SLG': '.450',
                'OBP weight': '50%',
                'SLG weight': '50%',
            },
        ])
        st.write(
            'Role score = 100 × '
            '[(OBP ÷ expected OBP × OBP weight) '
            '+ (SLG ÷ expected SLG × SLG weight)].'
        )
        st.caption(
            '100 means the hitter met the role’s expectations. '
            'Strong performance in one area can compensate '
            'for weaker performance in the other. '
            'For changing batting spots, expectations are weighted '
            'by recorded lineup plate appearances.'
        )

    if eligible:
        st.markdown('**Leading Cold Bat candidates**')
        table([
            {
                'Player': candidate['name'],
                'Role score': round(candidate['role_score'], 1),
                'Lineup PA': candidate['pa'],
            }
            for candidate in eligible[:3]
        ])
    else:
        st.info(
            'No eligible Cold Bat candidate was found. '
            'Confirm the skip below to continue.'
        )

    with st.form('cold_bat_review:' + run['id']):
        skip = st.checkbox(
            'No hitter meaningfully underperformed this week '
            '— skip Cold Bat punishment.',
            value=not bool(eligible),
        )

        selected_player = st.selectbox(
            'Cold Bat hitter',
            [None] + list(eligible_by_id),
            format_func=lambda pid: (
                eligible_by_id[pid]['name']
                if pid in eligible_by_id
                else 'Choose a hitter'
            ),
            disabled=not bool(eligible),
        )

        reason = st.text_area(
            'Reason for your decision',
            value=(
                'No eligible hitter meaningfully underperformed.'
                if not eligible else ''
            ),
        )

        confirmed = st.checkbox(
            'I confirm this week’s Cold Bat decision.'
        )

        submitted = st.form_submit_button(
            'Save Cold Bat decision',
            type='primary',
        )

        if submitted:
            decide_cold_bat(
                repo,
                fid,
                run['id'],
                player_id=selected_player,
                skip=skip,
                reason=reason,
                confirmed=confirmed,
            )
            st.rerun()

    return False


def render(repo, f):
    fid = f['id']
    state = f['state']

    if state == State.ACTIVE:
        st.info(
            'Your week is still active. The between-week offseason '
            'begins when the loss limit is reached.'
        )
        return

    if state == State.WHEEL:
        navigate('Spin the required wheel', 'Wheel Room')
        return

    if state == State.ENDED:
        run = repo.get('runs', f['current_run'])
        week = run.get('week_number', run['number'])

        st.write(
            f"Week {week} final record: "
            f"**{run['wins']}–{run['losses']}**"
        )

        if st.button(
            'Confirm ended week and select Weekly MVP',
            type='primary',
        ):
            confirm_end(repo, fid)
            st.rerun()

    elif state == State.MVP:
        run = repo.get('runs', f['current_run'])
        show_weekly_mvp(repo, fid, run)

    elif state in [State.ELIMINATION, State.MELTDOWN]:
        st.write(
            'Next: elimination'
            if state == State.ELIMINATION
            else 'Next: check configured 0–2 Meltdown'
        )

        if st.button('Continue offseason', type='primary'):
            progress(repo, fid)
            st.rerun()

    elif state == State.MOVES:
        run = repo.get('runs', f['current_run'])
        review_complete = show_cold_bat_review(repo, fid, run)

        st.subheader('Resolve banked moves')
        st.write(
            'Resolve consequences first, then rewards. Optional '
            'acquisitions can remain deferred for a later Event.'
        )
        navigate('Resolve banked moves', 'Banked Moves')

        manual = [
            challenge
            for challenge in repo.list('challenges', fid)
            if challenge['status'] == 'awaiting_manual'
        ]

        for challenge in manual:
            player = repo.get(
                'players', challenge['player_id']
            )
            name = (
                player['name'] if player else 'Player unavailable'
            )

            with st.form('challenge:' + challenge['id']):
                st.write(
                    name + ' — ' + challenge['description']
                )
                passed = st.checkbox('Challenge passed')
                evidence = st.text_input(
                    'Evidence / what happened'
                )

                if st.form_submit_button(
                    'Confirm challenge result'
                ):
                    confirm_manual(
                        repo,
                        fid,
                        challenge['id'],
                        passed,
                        evidence,
                    )
                    st.rerun()

        if not review_complete:
            st.caption(
                'Save your Cold Bat decision before proceeding.'
            )

        if st.button(
            'Proceed to roster reconstruction',
            type='primary',
            disabled=not review_complete,
        ):
            progress(repo, fid)
            st.rerun()

    elif state == State.REBUILD:
        navigate('Rebuild roster', 'Roster Manager')

        if st.button('Proceed to validation', type='primary'):
            progress(repo, fid)
            st.rerun()

    elif state == State.VALIDATION:
        result = validate(repo, fid)

        if result.valid:
            st.success(
                'Roster checks pass. Confirm in-game '
                'Event eligibility as well.'
            )

            if st.button(
                'Approve roster for next week',
                type='primary',
            ):
                finish_validation(repo, fid)
                st.rerun()
        else:
            for error in result.errors:
                st.warning(error)

            navigate('Fix roster assignments', 'Roster Manager')
            navigate('Resolve outstanding moves', 'Banked Moves')

    elif state in [State.SETUP, State.READY]:
        navigate('Review roster', 'Roster Manager')

        if st.button(
            'Start next week at 0–0',
            type='primary',
        ):
            start_run(repo, fid)
            st.rerun()
