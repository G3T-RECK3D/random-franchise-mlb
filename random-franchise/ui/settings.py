import json
import math
import streamlit as st

from services.franchise_service import settings, save_settings, audit
from services.roster_service import locked
from models.domain import RuleError
from ui.game_entry import correction


def validate_wedges(wedges, valid_wheels):
    effects = {
        'acquire', 'dfa', 'demote', 'trade', 'review', 'none',
        'protect', 'unprotect', 'hot_seat', 'arrangement',
        'challenge', 'tag', 'extra_spin', 'call_up',
        'cancel_elimination', 'save_dfa', 'reunion',
    }

    if (
        not isinstance(wedges, list)
        or not wedges
        or any(not isinstance(wedge, dict) for wedge in wedges)
    ):
        raise RuleError('Wedges must be a nonempty list of JSON objects.')

    identifiers = [wedge.get('id') for wedge in wedges]
    if (
        any(
            not isinstance(identifier, str) or not identifier.strip()
            for identifier in identifiers
        )
        or len(set(identifiers)) != len(identifiers)
    ):
        raise RuleError('Every wedge needs a distinct, nonempty string ID.')

    for wedge in wedges:
        weight = wedge.get('weight')
        if (
            not isinstance(wedge.get('text'), str)
            or not wedge['text'].strip()
            or isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or weight < 0
            or wedge.get('effect') not in effects
        ):
            raise RuleError(
                'Every wedge needs text, a nonnegative numeric weight, '
                'and a supported effect.'
            )

        if (
            wedge.get('follow_up')
            and wedge['follow_up'] not in valid_wheels
        ):
            raise RuleError('Unknown follow-up wheel.')

        quantity = wedge.get('quantity', 1)
        if type(quantity) is not int or not 1 <= quantity <= 4:
            raise RuleError('Quantity must be an integer 1–4.')

        if not isinstance(wedge.get('active', True), bool):
            raise RuleError('Active must be true or false.')

        if not isinstance(wedge.get('eligibility', {}), dict):
            raise RuleError('Wedge eligibility must be a JSON object.')

        if wedge['effect'] == 'reunion':
            if quantity != 1 or wedge.get('follow_up'):
                raise RuleError(
                    'Reunion Signing returns one card and cannot '
                    'have a follow-up wheel.'
                )
            if wedge.get('timing', 'banked') != 'banked':
                raise RuleError('Reunion Signing must use banked timing.')

    if not any(
        wedge.get('active', True) and wedge['weight'] > 0
        for wedge in wedges
    ):
        raise RuleError('Keep at least one active weighted wedge.')


def render(repo, f):
    fid = f['id']
    cfg = settings(repo, fid)

    with st.expander('Restore previous Event seasons'):
        from services.franchise_service import setup_recovered_seasons

        st.write('Selected franchise: **' + f['name'] + '**')
        st.write('Season 1: 2026 Wildcard Series Event — completed')
        st.write('Season 2: 2026 Division Series Event — current')

        if not repo.list('runs', fid) and not repo.list('games', fid):
            if st.button(
                'Set up these two seasons',
                key='recover_seasons:' + fid,
            ):
                setup_recovered_seasons(repo, fid)
                st.rerun()
        else:
            st.info(
                'Recovery setup is available before adding weeks or games.'
            )

        for season in sorted(
            repo.list('seasons', fid),
            key=lambda item: item['number'],
        ):
            st.write(
                f"Season {season['number']}: {season['name']}"
                f" — {season['status']}"
            )

    st.subheader('Back up your complete app data')
    st.caption(
        'Download a full copy of your saved app data, including seasons, '
        'franchises, games, stats, wheels, and audits. '
        'The download uses the SQLite backup format.'
    )
    st.download_button(
        'Download full SQLite backup',
        repo.backup_bytes(),
        'random_franchise_backup.db',
        'application/octet-stream',
    )

    if locked(repo, fid):
        st.info(
            'Rules and wheel settings are editable between weeks. '
            'Game/stat corrections remain available below.'
        )
    else:
        with st.form('settings:' + fid):
            st.subheader('Challenge and Event rules')
            st.caption(
                'Edit loss limits, milestones, tag cap, meltdown, '
                'roster sizes, average OVR cap, Event restrictions, '
                'dates, cooldown, and special wheel availability.'
            )
            text = st.text_area(
                'Settings JSON',
                value=json.dumps(cfg, indent=2),
                height=420,
            )
            if st.form_submit_button('Save rules'):
                try:
                    values = json.loads(text)
                except ValueError:
                    raise RuleError('Invalid settings JSON.')

                save_settings(repo, fid, values)
                st.rerun()

        wheels = repo.list('wheels', fid)
        labels = {
            wheel['id']: wheel['display_name']
            for wheel in wheels
        }

        if not wheels:
            st.info('No wheels are configured for this franchise.')
        else:
            wid = st.selectbox(
                'Wheel to edit',
                list(labels),
                format_func=labels.get,
                key='settings_wheel:' + fid,
            )
            wheel = repo.get('wheels', wid)
            valid_wheels = {
                item['wheel_id'] for item in wheels
            }

            with st.form('wheel:' + wid):
                text = st.text_area(
                    'Wedges JSON '
                    '(weights, active flags, effects, eligibility, '
                    'follow-up wheel)',
                    value=json.dumps(wheel['wedges'], indent=2),
                    height=420,
                )
                if st.form_submit_button('Save wheel configuration'):
                    try:
                        wedges = json.loads(text)
                    except ValueError:
                        raise RuleError('Invalid wheel JSON.')

                    validate_wedges(wedges, valid_wheels)

                    with repo.transaction():
                        current = repo.get('wheels', wid)
                        before = dict(current)
                        current['wedges'] = wedges
                        repo.put('wheels', current)
                        audit(
                            repo, fid, 'wheel_configuration',
                            before, current, 'Wheel editor',
                        )
                    st.rerun()

            if wheel['wheel_id'] == 'front_office':
                st.caption(
                    'Reunion Signing randomly selects an eligible former '
                    'card with a saved appearance in an earlier season. '
                    'It is excluded from spins when no qualifying card '
                    'is available.'
                )

                already_added = any(
                    wedge.get('effect') == 'reunion'
                    for wedge in wheel['wedges']
                )

                if already_added:
                    st.info(
                        'Reunion Signing is configured. '
                        'Adjust its weight or active flag in the JSON above.'
                    )
                elif st.button(
                    'Add Reunion Signing to this wheel',
                    key='add_reunion:' + fid,
                ):
                    with repo.transaction():
                        current = repo.get('wheels', wid)

                        if not any(
                            wedge.get('effect') == 'reunion'
                            for wedge in current['wedges']
                        ):
                            used_ids = {
                                wedge['id']
                                for wedge in current['wedges']
                            }
                            identifier = 'reunion_signing'
                            suffix = 2
                            while identifier in used_ids:
                                identifier = f'reunion_signing_{suffix}'
                                suffix += 1

                            new_wedge = {
                                'id': identifier,
                                'text': 'Reunion Signing',
                                'weight': 1,
                                'active': True,
                                'category': 'acquire',
                                'effect': 'reunion',
                                'timing': 'banked',
                                'follow_up': None,
                                'eligibility': {},
                                'quantity': 1,
                                'description': (
                                    'Bring back the randomly selected '
                                    'Event-eligible card from a previous '
                                    'season. Reuse its existing player '
                                    'entry and preserve its stats. '
                                    'Resolve during offseason, then '
                                    'arrange the card in Roster Manager.'
                                ),
                            }

                            before = dict(current)
                            current['wedges'] = (
                                list(current['wedges']) + [new_wedge]
                            )
                            validate_wedges(
                                current['wedges'], valid_wheels,
                            )
                            repo.put('wheels', current)
                            audit(
                                repo, fid, 'wheel_configuration',
                                before, current,
                                'Added Reunion Signing with weight 1.',
                            )

                    st.rerun()

    with st.expander('Administrative corrections'):
        correction(repo, f)

    with st.expander('Delete an empty test franchise'):
        history_tables = [
            'players', 'runs', 'games', 'stats', 'spins', 'moves',
            'rewards', 'challenges', 'snapshots', 'corrections', 'tags',
        ]
        candidates = [
            franchise
            for franchise in repo.list('franchises')
            if franchise['id'] != fid
            and franchise['name'].strip().casefold().startswith('test')
            and not any(
                repo.list(table_name, franchise['id'])
                for table_name in history_tables
            )
        ]

        if not candidates:
            st.info(
                'No other empty test franchises are available to delete.'
            )
        else:
            choices = {
                item['id']: item for item in candidates
            }
            delete_id = st.selectbox(
                'Empty test franchise to delete',
                list(choices),
                format_func=lambda identifier: (
                    choices[identifier]['name']
                    + ' · ' + choices[identifier].get('event', '')
                    + ' · ID ending ' + identifier[-6:]
                ),
                key='delete_empty_test_target',
            )
            confirmed = st.checkbox(
                'Permanently delete this empty test franchise.',
                key='delete_empty_test_confirm',
            )

            if st.button(
                'Delete empty test franchise',
                disabled=not confirmed,
            ):
                with repo.transaction():
                    selected = repo.get('franchises', delete_id)
                    if (
                        not selected
                        or delete_id == fid
                        or not selected['name'].strip().casefold()
                        .startswith('test')
                        or any(
                            repo.list(table_name, delete_id)
                            for table_name in history_tables
                        )
                    ):
                        raise RuleError(
                            'Only another empty test franchise can be deleted.'
                        )

                    for table_name in ['wheels', 'settings', 'seasons']:
                        for row in repo.list(table_name, delete_id):
                            repo.delete(table_name, row['id'])

                    repo.delete('franchises', delete_id)

                st.rerun()
