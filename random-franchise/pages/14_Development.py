import streamlit as st

from models.domain import RuleError
from services.challenge_service import (
    assign_development,
    development_progress,
    metric_value,
)
from services.franchise_service import audit
from services.stat_engine import aggregate
from ui.common import run_page


def render(repo, f):
    fid = f['id']
    st.subheader('🌱 Player development')
    st.caption(
        'Complete your assigned goal during the entire next week/run. '
        'Successful upgrades are banked until between weeks.'
    )

    run = (
        repo.get('runs', f['current_run'])
        if f.get('current_run')
        else None
    )

    with st.expander('Restore Albies and Headley’s challenges'):
        st.write('**Ozzie Albies:** 2 extra-base hits next run.')
        st.write('**Chase Headley:** 2 home runs next run.')
        st.caption(
            'Their previously saved games do not count. '
            'These challenges begin when you start the next week. '
            'Existing open challenges or pending upgrades prevent duplicates.'
        )

        if not run:
            st.info('Start the current week before assigning these challenges.')
        else:
            players = [
                repo.get('players', pid)
                for pid in run['roster_ids']
            ]
            players = [player for player in players if player]

            selections = {}
            for name, goal in [
                ('Ozzie Albies', 'extra_base_hits'),
                ('Chase Headley', 'hr'),
            ]:
                matches = [
                    player for player in players
                    if player['name'].strip().casefold() == name.casefold()
                ]
                if not matches:
                    st.warning(name + ' is not in the current week’s roster.')
                    continue

                choices = {
                    player['id']: player for player in matches
                }
                pid = st.selectbox(
                    name + ' card',
                    list(choices),
                    format_func=lambda pid, choices=choices: (
                        choices[pid]['name']
                        + ' · '
                        + str(choices[pid]['ovr'])
                        + ' OVR · '
                        + choices[pid].get('version', '')
                    ),
                    key='restore_development:' + fid + ':' + goal,
                )
                selections[name] = (pid, goal)

            confirmed = st.checkbox(
                'Assign these goals for the next week, excluding games '
                'already played.',
                key='restore_development_confirm:' + fid,
            )

            if st.button(
                'Assign Albies and Headley challenges',
                disabled=not confirmed or len(selections) != 2,
                key='restore_development_apply:' + fid,
            ):
                try:
                    with repo.transaction():
                        current = repo.get('franchises', fid)
                        if current.get('current_run') != run['id']:
                            raise RuleError(
                                'The current week changed. Reload this page.'
                            )

                        created = []
                        skipped = []

                        for name, (pid, goal) in selections.items():
                            cid = assign_development(
                                repo,
                                fid,
                                run['id'],
                                pid,
                                reason=(
                                    'Manually restored early-quit standout; '
                                    'goal drawn before assignment.'
                                ),
                                goal=goal,
                            )
                            if cid:
                                created.append(name)
                                audit(
                                    repo,
                                    fid,
                                    'restore_development_challenge',
                                    None,
                                    repo.get('challenges', cid),
                                    'Restore previously earned development '
                                    'challenge without replaying games.',
                                    run['id'],
                                )
                            else:
                                skipped.append(name)

                    if created:
                        st.success('Assigned: ' + ', '.join(created))
                    if skipped:
                        st.info(
                            'Already has a development challenge this week, '
                            'an open challenge, or an upgrade waiting: '
                            + ', '.join(skipped)
                        )
                except RuleError as exc:
                    st.error(str(exc))

    challenges = [
        challenge
        for challenge in repo.list('challenges', fid)
        if challenge.get('reward') == 'upgrade'
    ]

    if not challenges:
        st.info('No development challenges have been assigned yet.')
        return

    labels = {
        'waiting_next_run': 'Starts next week',
        'active': 'In progress',
        'passed': 'Completed — upgrade earned',
        'failed': 'Not completed',
        'awaiting_manual': 'Awaiting confirmation',
    }

    for challenge in reversed(challenges):
        player = repo.get('players', challenge['player_id'])
        name = player['name'] if player else 'Unavailable player'

        with st.container(border=True):
            st.markdown('**' + name + '**')
            st.write(challenge['description'])
            st.caption(
                labels.get(challenge['status'], challenge['status'])
            )

            if challenge['status'] == 'waiting_next_run':
                st.info(
                    'Waiting for the next week to start. '
                    'Current-week stats do not count.'
                )
                continue

            if challenge['scope'] == 'three_games':
                progress = development_progress(repo, challenge)
                st.write(
                    f"Team games: {progress['games_used']} "
                    f"/ {progress['game_limit']}"
                )
                for metric, target in challenge.get('goals', {}).items():
                    value = metric_value(progress['totals'], metric)
                    st.write(f'{metric}: {value} / {target}')
                continue

            target_run = repo.get('runs', challenge.get('run_id'))
            if not target_run or not player:
                st.caption('Challenge details are unavailable.')
                continue

            st.caption(
                'Challenge week: '
                + str(target_run.get('week_number', target_run['number']))
            )

            if challenge.get('metric'):
                totals = aggregate(
                    repo,
                    fid,
                    player,
                    target_run['id'],
                )
                value = metric_value(totals, challenge['metric'])
                target = challenge['threshold']

                metric_labels = {
                    'hr': 'Home runs',
                    'h': 'Hits',
                    'extra_base_hits': 'Extra-base hits',
                    'rbi': 'RBI',
                    'times_on_base': 'Times on base',
                    'so': 'Strikeouts',
                }
                label = metric_labels.get(
                    challenge['metric'],
                    challenge['metric'],
                )
                st.write(f'{label}: **{value} / {target}**')
                st.progress(
                    min(1.0, max(0.0, value / target))
                    if target > 0
                    else 0.0
                )


run_page('Development', render, obs=False)
