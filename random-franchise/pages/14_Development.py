
"""Player development dashboard: current goals, upcoming, and history.

This page only organizes and displays saved challenges. Challenge evaluation,
rewards, and underlying player/stat records remain controlled by services.
"""

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


METRIC_LABELS = {
    'hr': 'Home runs',
    'h': 'Hits',
    'extra_base_hits': 'Extra-base hits',
    'rbi': 'RBI',
    'times_on_base': 'Times on base',
    'so': 'Strikeouts',
    'outs': 'Outs recorded',
    'w': 'Wins',
    'sv': 'Saves',
}

STATUS_LABELS = {
    'waiting_next_run': 'Starts next week',
    'active': 'In progress',
    'awaiting_manual': 'Needs confirmation',
    'passed': 'Completed — upgrade earned',
    'failed': 'Not achieved',
}


def _week_label(run):
    if not run:
        return 'Unknown week'
    week = run.get('week_number', run.get('number', '?'))
    return 'Week ' + str(week)


def _sort_key(challenge, runs):
    run = runs.get(challenge.get('run_id'))
    try:
        number = int(run.get('number', 0)) if run else 0
    except (ValueError, TypeError):
        number = 0
    return (
        number,
        str(challenge.get('created_at', '')),
        str(challenge.get('id', '')),
    )


def _groups(repo, challenges, runs):
    """Classify for display without changing saved challenge status."""
    groups = {
        'current': [],
        'upcoming': [],
        'completed': [],
        'history': [],
    }

    for challenge in challenges:
        status = challenge.get('status', '')
        source_run = runs.get(challenge.get('run_id'))

        if status == 'passed':
            groups['completed'].append((challenge, None))

        elif status == 'failed':
            groups['history'].append((challenge, None))

        elif status == 'waiting_next_run':
            groups['upcoming'].append((challenge, None))

        elif status == 'awaiting_manual':
            groups['current'].append((challenge, None))

        elif status == 'active':
            stale = bool(
                source_run and source_run.get('ended_at')
            )

            if challenge.get('scope') == 'three_games':
                try:
                    progress = development_progress(
                        repo, challenge
                    )
                    stale = bool(progress['closed'])
                except (KeyError, TypeError, ValueError):
                    pass

            if stale:
                groups['history'].append((
                    challenge,
                    'Needs review — older open challenge',
                ))
            else:
                groups['current'].append((challenge, None))

        else:
            groups['history'].append((
                challenge,
                'Needs review — unknown status',
            ))

    for name in groups:
        groups[name].sort(
            key=lambda item: _sort_key(item[0], runs),
            reverse=True,
        )

    return groups


def _details(repo, fid, challenge, runs):
    status = challenge.get('status')
    run = runs.get(challenge.get('run_id'))
    player = repo.get(
        'players', challenge.get('player_id')
    )

    st.write(
        challenge.get('description')
        or 'No goal description available.'
    )

    if status == 'waiting_next_run':
        st.info(
            'This goal begins when the next week starts. '
            'Stats from the week when it was earned do not count.'
        )
        return

    if run:
        st.caption(
            'Challenge week: ' + _week_label(run)
        )

    if status == 'awaiting_manual':
        st.info(
            'This challenge needs manual confirmation '
            'in the offseason workflow.'
        )

    if challenge.get('scope') == 'three_games':
        try:
            progress = development_progress(
                repo, challenge
            )
        except (KeyError, TypeError, ValueError):
            st.caption(
                'Legacy challenge progress is unavailable.'
            )
            return

        st.write(
            'Team games: '
            + str(progress['games_used'])
            + ' / '
            + str(progress['game_limit'])
        )

        for metric, target in challenge.get(
            'goals', {}
        ).items():
            value = metric_value(
                progress['totals'], metric
            )
            st.write(
                METRIC_LABELS.get(metric, metric)
                + ': **'
                + str(value)
                + ' / '
                + str(target)
                + '**'
            )
        return

    if not run or not player:
        st.caption(
            'Saved player or challenge-week '
            'details are unavailable.'
        )
        return

    if challenge.get('metric'):
        totals = aggregate(
            repo,
            fid,
            player,
            run['id'],
        )

        value = metric_value(
            totals, challenge['metric']
        )
        target = challenge.get('threshold', 1)
        label = METRIC_LABELS.get(
            challenge['metric'],
            challenge['metric'],
        )

        st.write(
            label + ': **'
            + f'{value:g} / {target:g}'
            + '**'
        )

        if (
            isinstance(target, (float, int))
            and target > 0
        ):
            st.progress(
                min(
                    1.0,
                    max(0.0, float(value) / target),
                )
            )

    if status == 'passed':
        move = repo.get(
            'moves',
            'challenge:' + str(
                challenge.get('id', '')
            ),
        )

        if move:
            statuses = {
                'pending': (
                    'Upgrade earned — waiting in Banked Moves'
                ),
                'deferred': (
                    'Upgrade earned — saved for later'
                ),
                'resolved': 'Upgrade reward resolved',
                'canceled': 'Upgrade reward canceled',
            }

            st.caption(
                statuses.get(
                    move.get('status'),
                    'Upgrade reward recorded',
                )
            )
        else:
            st.caption(
                'Challenge passed. Check Banked Moves '
                'for its upgrade reward.'
            )


def _challenge_card(
    repo, fid, entry, runs, compact=False
):
    challenge, override = entry
    player = repo.get(
        'players', challenge.get('player_id')
    )

    name = (
        player['name']
        if player else 'Unavailable player'
    )

    run = runs.get(challenge.get('run_id'))

    status = override or STATUS_LABELS.get(
        challenge.get('status'),
        str(challenge.get('status', 'Unknown')),
    )

    if compact:
        with st.expander(
            name + ' · '
            + _week_label(run)
            + ' · '
            + status
        ):
            _details(
                repo, fid, challenge, runs
            )

            if override:
                st.warning(
                    'This saved challenge is still marked '
                    'active even though its deadline appears '
                    'to have passed. It has NOT been '
                    'automatically marked as failed or '
                    'changed in the database.'
                )
    else:
        with st.container(border=True):
            st.markdown('**' + name + '**')
            st.caption(status)

            _details(
                repo, fid, challenge, runs
            )


def _cards(
    repo,
    fid,
    entries,
    runs,
    empty_message,
    compact=False,
):
    if not entries:
        st.info(empty_message)
        return

    if compact:
        for entry in entries:
            _challenge_card(
                repo,
                fid,
                entry,
                runs,
                compact=True,
            )
    else:
        columns = st.columns(2)

        for index, entry in enumerate(entries):
            with columns[index % 2]:
                _challenge_card(
                    repo,
                    fid,
                    entry,
                    runs,
                )


def _restoration(repo, fid, run):
    """Preserve the Albies/Headley restoration workflow."""

    with st.expander(
        'Restore Albies and Headley’s challenges'
    ):
        st.write(
            '**Ozzie Albies:** 2 extra-base hits next run.'
        )
        st.write(
            '**Chase Headley:** 2 home runs next run.'
        )

        st.caption(
            'Their previously saved games do not count. '
            'These challenges begin when you start the next week. '
            'Existing open challenges or pending upgrades '
            'prevent duplicates.'
        )

        if not run:
            st.info(
                'Start the current week before assigning '
                'these challenges.'
            )
            return

        players = [
            repo.get('players', pid)
            for pid in run['roster_ids']
        ]

        players = [
            player for player in players if player
        ]

        selections = {}

        for name, goal in [
            ('Ozzie Albies', 'extra_base_hits'),
            ('Chase Headley', 'hr'),
        ]:
            matches = [
                player
                for player in players
                if player['name'].strip().casefold()
                == name.casefold()
            ]

            if not matches:
                st.warning(
                    name
                    + ' is not in the current week’s roster.'
                )
                continue

            choices = {
                player['id']: player
                for player in matches
            }

            pid = st.selectbox(
                name + ' card',
                list(choices),
                format_func=(
                    lambda pid, choices=choices: (
                        choices[pid]['name']
                        + ' · '
                        + str(choices[pid]['ovr'])
                        + ' OVR · '
                        + str(
                            choices[pid].get('version', '')
                        )
                    )
                ),
                key=(
                    'restore_development:'
                    + fid + ':' + goal
                ),
            )

            selections[name] = (pid, goal)

        confirmed = st.checkbox(
            'Assign these goals for the next week, '
            'excluding games already played.',
            key='restore_development_confirm:' + fid,
        )

        if st.button(
            'Assign Albies and Headley challenges',
            disabled=(
                not confirmed
                or len(selections) != 2
            ),
            key='restore_development_apply:' + fid,
        ):
            try:
                with repo.transaction():
                    current = repo.get(
                        'franchises', fid
                    )

                    if (
                        current.get('current_run')
                        != run['id']
                    ):
                        raise RuleError(
                            'The current week changed. '
                            'Reload this page.'
                        )

                    created = []
                    skipped = []

                    for name, (
                        pid, goal
                    ) in selections.items():
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
                                repo.get(
                                    'challenges', cid
                                ),
                                'Restore previously earned development '
                                'challenge without replaying games.',
                                run['id'],
                            )
                        else:
                            skipped.append(name)

                if created:
                    st.success(
                        'Assigned: '
                        + ', '.join(created)
                    )

                if skipped:
                    st.info(
                        'Already has a development challenge '
                        'this week, an open challenge, or '
                        'an upgrade waiting: '
                        + ', '.join(skipped)
                    )

            except RuleError as exc:
                st.error(str(exc))


def render(repo, f):
    fid = f['id']

    st.subheader('🌱 Player development')

    st.caption(
        'Track goals across weeks. Challenges earned this '
        'week begin next week. Successful upgrades are '
        'banked for the offseason.'
    )

    run = (
        repo.get('runs', f['current_run'])
        if f.get('current_run')
        else None
    )

    challenges = [
        challenge
        for challenge in repo.list('challenges', fid)
        if challenge.get('reward') == 'upgrade'
    ]

    runs = {
        r['id']: r
        for r in repo.list('runs', fid)
    }

    groups = _groups(repo, challenges, runs)

    a, b, c, d = st.columns(4)

    a.metric(
        'Current', len(groups['current'])
    )
    b.metric(
        'Starts next week', len(groups['upcoming'])
    )
    c.metric(
        'Completed', len(groups['completed'])
    )
    d.metric(
        'History', len(groups['history'])
    )

    needs_review = sum(
        1
        for _, issue in groups['history']
        if issue
    )

    if needs_review:
        st.warning(
            str(needs_review)
            + ' older development challenge(s) may need '
            'a status review. They remain unchanged in '
            'your saved data and are listed in History.'
        )

    tabs = st.tabs([
        'Current challenges',
        'Starts next week',
        'Completed',
        'History',
    ])

    with tabs[0]:
        st.caption(
            'Active goals and challenges awaiting confirmation.'
        )

        _cards(
            repo,
            fid,
            groups['current'],
            runs,
            'No development challenges are currently in progress.',
        )

    with tabs[1]:
        st.caption(
            'These goals begin with the next run; '
            'current stats do not count.'
        )

        _cards(
            repo,
            fid,
            groups['upcoming'],
            runs,
            'No development challenges are waiting for next week.',
        )

    with tabs[2]:
        st.caption(
            'Completed goals and their earned upgrade rewards.'
        )

        _cards(
            repo,
            fid,
            groups['completed'],
            runs,
            'No development challenges have been completed yet.',
            compact=True,
        )

    with tabs[3]:
        st.caption(
            'Unsuccessful and older challenges, '
            'kept for your franchise history. '
            'Open an entry to see its original goal '
            'and final recorded progress.'
        )

        _cards(
            repo,
            fid,
            groups['history'],
            runs,
            'No unsuccessful or older development '
            'challenges to show.',
            compact=True,
        )

    st.divider()

    st.caption(
        'Previously earned development goals'
    )

    _restoration(repo, fid, run)


run_page('Development', render, obs=False)
