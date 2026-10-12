import copy
import json
import math

import streamlit as st

from models.domain import RuleError, State
from services.franchise_service import settings, save_settings, audit
from services.roster_service import locked
from ui.game_entry import correction


FEATURE_VERSION = 1

COLD_BAT_EFFECTS = {
    'cold_bat_hot_seat',
    'cold_bat_order',
    'cold_bat_bench',
    'downgrade',
}


def validate_wedges(wedges, valid_wheels):
    effects = {
        'acquire', 'dfa', 'demote', 'trade', 'review', 'none',
        'protect', 'unprotect', 'hot_seat', 'arrangement',
        'challenge', 'tag', 'extra_spin', 'call_up',
        'cancel_elimination', 'save_dfa', 'reunion',
        'mvp_upgrade',
    } | COLD_BAT_EFFECTS

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

        if wedge['effect'] in (
            {'reunion', 'mvp_upgrade'} | COLD_BAT_EFFECTS
        ):
            if quantity != 1 or wedge.get('follow_up'):
                raise RuleError(
                    'Reunion, MVP upgrade, and Cold Bat wedges '
                    'must affect one card without a follow-up wheel.'
                )
            if wedge.get('timing', 'banked') != 'banked':
                raise RuleError(
                    'Reunion, MVP upgrade, and Cold Bat wedges '
                    'must use banked timing.'
                )

    if not any(
        wedge.get('active', True) and wedge['weight'] > 0
        for wedge in wedges
    ):
        raise RuleError('Keep at least one active weighted wedge.')


def unique_wedge_id(wedges, base):
    used = {wedge['id'] for wedge in wedges}
    identifier = base
    suffix = 2

    while identifier in used:
        identifier = f'{base}_{suffix}'
        suffix += 1

    return identifier


def cold_bat_wedges():
    definitions = [
        (
            'cold_bat_hot_seat',
            'Hot Seat Next Week',
            50,
            'cold_bat_hot_seat',
            'Put the selected Cold Bat hitter on the hot seat '
            'for the next week.',
        ),
        (
            'cold_bat_order',
            'Start Next Week Batting 7–9',
            25,
            'cold_bat_order',
            'Arrange the selected Cold Bat hitter in batting '
            'spot 7, 8, or 9 to start the next week. '
            'Verify the arrangement in Banked Moves.',
        ),
        (
            'cold_bat_bench',
            'Start Next Week on the Bench',
            20,
            'cold_bat_bench',
            'Move the selected Cold Bat hitter to the bench '
            'to start the next week. Verify the arrangement '
            'in Banked Moves.',
        ),
        (
            'cold_bat_downgrade',
            'Downgrade This Player’s Card',
            5,
            'downgrade',
            'Use the next available lower-rated Event-legal card '
            'of the selected Cold Bat hitter. If no lower-rated '
            'legal card exists, use Hot Seat Next Week instead.',
        ),
    ]

    return [
        {
            'id': identifier,
            'text': text,
            'weight': weight,
            'active': True,
            'category': 'consequence',
            'effect': effect,
            'timing': 'banked',
            'follow_up': None,
            'eligibility': {},
            'quantity': 1,
            'description': description,
        }
        for identifier, text, weight, effect, description in definitions
    ]


def install_weekly_wheels(repo, fid):
    """Install once without resetting later manual weight edits."""
    with repo.transaction():
        franchise = repo.get('franchises', fid)
        if not franchise:
            raise RuleError('Select a valid franchise.')

        mvp_id = f'{fid}:mvp'
        cold_id = f'{fid}:cold_bat'

        mvp = repo.get('wheels', mvp_id)
        cold = repo.get('wheels', cold_id)

        if not mvp:
            raise RuleError('The existing Weekly MVP wheel was not found.')

        mvp_ready = (
            mvp.get('weekly_features_version') == FEATURE_VERSION
        )
        cold_ready = (
            cold
            and cold.get('weekly_features_version') == FEATURE_VERSION
        )

        if mvp_ready and cold_ready:
            return False

        if franchise.get('queue'):
            raise RuleError(
                'Finish the currently queued wheels before installing.'
            )

        if franchise['state'] in [State.REBUILD, State.VALIDATION]:
            raise RuleError(
                'Finish roster reconstruction and validation first. '
                'Install during the next active week so the Cold Bat '
                'review follows the complete offseason workflow.'
            )

        if cold and not cold_ready:
            raise RuleError(
                'A different Cold Bat wheel already exists. '
                'It was left unchanged to preserve its configuration.'
            )

        valid_wheels = {
            wheel['wheel_id']
            for wheel in repo.list('wheels', fid)
        } | {'cold_bat'}

        if not mvp_ready:
            before = copy.deepcopy(mvp)

            # Retain the existing outcomes and their relative odds.
            # Replace any earlier MVP-upgrade wedge with one 5% wedge.
            wedges = [
                copy.deepcopy(wedge)
                for wedge in mvp['wedges']
                if wedge.get('effect') != 'mvp_upgrade'
            ]
            validate_wedges(wedges, valid_wheels)

            active_total = math.fsum(
                wedge['weight']
                for wedge in wedges
                if wedge.get('active', True)
                and wedge['weight'] > 0
            )

            if not math.isfinite(active_total) or active_total <= 0:
                raise RuleError(
                    'The MVP wheel needs active weighted outcomes.'
                )

            for wedge in wedges:
                if wedge.get('active', True) and wedge['weight'] > 0:
                    wedge['weight'] = (
                        wedge['weight'] / active_total * 95
                    )

            wedges.append({
                'id': unique_wedge_id(wedges, 'weekly_mvp_upgrade'),
                'text': 'Upgrade the Weekly MVP’s Card',
                'weight': 5,
                'active': True,
                'category': 'acquire',
                'effect': 'mvp_upgrade',
                'timing': 'banked',
                'follow_up': None,
                'eligibility': {},
                'quantity': 1,
                'description': (
                    'Upgrade the Weekly MVP to their next available '
                    'higher-rated Event-legal card. This reward stays '
                    'with the MVP. If no higher-rated legal card exists, '
                    'confirm temporary protection instead.'
                ),
            })

            validate_wedges(wedges, valid_wheels)
            mvp['wedges'] = wedges
            mvp['weekly_features_version'] = FEATURE_VERSION
            repo.put('wheels', mvp)

            audit(
                repo,
                fid,
                'wheel_configuration',
                before,
                mvp,
                'Added a 5% configured Weekly MVP upgrade chance; '
                'preserved relative weights of existing active outcomes.',
            )

        if not cold_ready:
            cold = {
                'id': cold_id,
                'franchise_id': fid,
                'wheel_id': 'cold_bat',
                'display_name': 'Cold Bat',
                'wedges': cold_bat_wedges(),
                'weekly_features_version': FEATURE_VERSION,
            }
            validate_wedges(cold['wedges'], valid_wheels)
            repo.put('wheels', cold)

            audit(
                repo,
                fid,
                'wheel_configuration',
                None,
                cold,
                'Installed Cold Bat wheel: 50% hot seat, '
                '25% batting order, 20% bench, 5% downgrade.',
            )

        return True


def show_weekly_wheel_installation(repo, f):
    fid = f['id']

    with st.expander('Install Weekly MVP and Cold Bat wheels'):
        st.write(
            'Weekly MVP: add a 5% card-upgrade wedge while preserving '
            'the relative odds of the existing active outcomes.'
        )
        st.caption(
            'The 5% is the configured share. If the wheel engine '
            'excludes other outcomes during a particular spin, '
            'the effective probability can change.'
        )

        st.write(
            'Cold Bat: 50% Hot Seat Next Week, '
            '25% start batting 7–9, '
            '20% start on the bench, '
            '5% downgrade the selected player’s card.'
        )
        st.caption(
            'The offseason page asks you to choose a qualifying hitter '
            'or skip punishment. Installation applies to upcoming spins '
            'and does not replay previously completed wheels.'
        )

        mvp = repo.get('wheels', f'{fid}:mvp')
        cold = repo.get('wheels', f'{fid}:cold_bat')
        installed = (
            mvp
            and cold
            and mvp.get('weekly_features_version') == FEATURE_VERSION
            and cold.get('weekly_features_version') == FEATURE_VERSION
        )

        if installed:
            st.success(
                'Both wheels are installed. Edit their weights below '
                'between weeks if you want to change them.'
            )
        elif st.button(
            'Install/update these wheels',
            key='install_weekly_wheels:' + fid,
            type='primary',
        ):
            install_weekly_wheels(repo, fid)
            st.rerun()


def show_reunion_button(repo, fid, wid, wheel, valid_wheels):
    if wheel['wheel_id'] != 'front_office':
        return

    st.caption(
        'Reunion Signing randomly selects an eligible former card '
        'with a saved appearance in an earlier season. It is excluded '
        'when no qualifying card is available.'
    )

    if any(
        wedge.get('effect') == 'reunion'
        for wedge in wheel['wedges']
    ):
        st.info(
            'Reunion Signing is configured. Adjust its weight '
            'or active flag in the JSON above.'
        )
        return

    if st.button(
        'Add Reunion Signing to this wheel',
        key='add_reunion:' + fid,
    ):
        with repo.transaction():
            current = repo.get('wheels', wid)

            if not any(
                wedge.get('effect') == 'reunion'
                for wedge in current['wedges']
            ):
                before = copy.deepcopy(current)
                wedge = {
                    'id': unique_wedge_id(
                        current['wedges'], 'reunion_signing'
                    ),
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
                        'Bring back the randomly selected Event-eligible '
                        'card from a previous season. Reuse its existing '
                        'player entry and preserve its stats. Resolve '
                        'during offseason, then arrange the card '
                        'in Roster Manager.'
                    ),
                }
                current['wedges'] = list(current['wedges']) + [wedge]
                validate_wedges(current['wedges'], valid_wheels)
                repo.put('wheels', current)
                audit(
                    repo, fid, 'wheel_configuration',
                    before, current,
                    'Added Reunion Signing with weight 1.',
                )

        st.rerun()


def show_wheel_editor(repo, fid):
    wheels = repo.list('wheels', fid)
    if not wheels:
        st.info('No wheels are configured for this franchise.')
        return

    labels = {
        wheel['id']: wheel['display_name']
        for wheel in wheels
    }
    wid = st.selectbox(
        'Wheel to edit',
        list(labels),
        format_func=labels.get,
        key='settings_wheel:' + fid,
    )
    wheel = repo.get('wheels', wid)
    valid_wheels = {item['wheel_id'] for item in wheels}

    with st.form('wheel:' + wid):
        text = st.text_area(
            'Wedges JSON '
            '(weights, active flags, effects, eligibility, follow-up wheel)',
            value=json.dumps(wheel['wedges'], indent=2),
            height=420,
        )
        if st.form_submit_button('Save wheel configuration'):
            try:
                wedges = json.loads(text)
            except ValueError:
                raise RuleError('Invalid wheel JSON.')

            validate_wedges(wedges, valid_wheels)

            fixed_effects = COLD_BAT_EFFECTS | {'mvp_upgrade'}
            for wedge in wedges:
                effect = wedge['effect']
                if (
                    effect in COLD_BAT_EFFECTS
                    and wheel['wheel_id'] != 'cold_bat'
                ):
                    raise RuleError(
                        'Cold Bat effects belong on the Cold Bat wheel.'
                    )
                if (
                    effect == 'mvp_upgrade'
                    and wheel['wheel_id'] != 'mvp'
                ):
                    raise RuleError(
                        'MVP upgrade belongs on the Weekly MVP wheel.'
                    )
                if (
                    effect in fixed_effects
                    and wedge.get('eligibility')
                ):
                    raise RuleError(
                        'Use empty eligibility {} for MVP upgrade '
                        'and Cold Bat wedges. Their selected player '
                        'is checked by the wheel service.'
                    )

            with repo.transaction():
                current = repo.get('wheels', wid)
                before = copy.deepcopy(current)
                current['wedges'] = wedges
                repo.put('wheels', current)
                audit(
                    repo, fid, 'wheel_configuration',
                    before, current, 'Wheel editor',
                )
            st.rerun()

    active = [
        wedge for wedge in wheel['wedges']
        if wedge.get('active', True) and wedge['weight'] > 0
    ]
    total = math.fsum(wedge['weight'] for wedge in active)
    if total:
        st.caption(
            'Configured chances before eligibility filtering: '
            + ' · '.join(
                f"{wedge['text']}: "
                f"{wedge['weight'] / total * 100:.1f}%"
                for wedge in active
            )
        )

    show_reunion_button(repo, fid, wid, wheel, valid_wheels)


def show_empty_test_deletion(repo, fid):
    history_tables = [
        'players', 'runs', 'games', 'stats', 'spins', 'moves',
        'rewards', 'challenges', 'snapshots', 'corrections', 'tags',
    ]

    with st.expander('Delete an empty test franchise'):
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
            return

        choices = {item['id']: item for item in candidates}
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

    # This one-time installation is available during an active week.
    show_weekly_wheel_installation(repo, f)

    if locked(repo, fid):
        st.info(
            'Regular rule and wheel edits are available between weeks. '
            'The installation above is available during an active week. '
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

        show_wheel_editor(repo, fid)

    with st.expander('Administrative corrections'):
        correction(repo, f)

    show_empty_test_deletion(repo, fid)
