from datetime import date
import streamlit as st
from models.domain import State,uid,RuleError
from services.stat_engine import validate_line
from services.game_engine import record_game,correct_game
from ui.forms import stat_fields
from ui.common import navigate


def render(repo,f):
    fid=f['id']
    run=repo.get('runs',f['current_run']) if f['current_run'] else None

    if f['state']!=State.ACTIVE or not run:
        st.info('Game entry is locked. Finish the current wheel or offseason action.')
        navigate('Open required wheel','Wheel Room') if f['state']==State.WHEEL else navigate('Open offseason','Offseason')
        return

    key='draft:'+run['id']

    if key not in st.session_state:
        with st.container():
            a,b,c=st.columns(3)
            result=a.selectbox('Result',['W','L'])
            opponent=b.text_input('Opponent (optional)')
            played=c.date_input('Game date',value=date.today())
            include=st.checkbox('Include scores')

            a,b=st.columns(2)
            own=a.number_input('Your score',0,99,0)
            opp=b.number_input('Opponent score',0,99,0)
            notes=st.text_area('Game notes')

            opponent_quit = st.checkbox('Opponent quit / conceded')
            if opponent_quit:
                quit_inning = st.number_input(
                    'Inning the opponent quit',
                    min_value=1,
                    max_value=30,
                    value=2,
                    step=1,
                )

                candidates = [
                    repo.get('players', pid)
                    for pid in run['roster_ids']
                ]
                candidates = [p for p in candidates if p]
                names = {
                    p['id']: p['name'] + ' · ' + p['version']
                    for p in candidates
                }
                standout = st.selectbox(
                    'Standout player',
                    [None] + list(names),
                    format_func=lambda pid: names.get(
                        pid, 'Choose a player'
                    ),
                )

                qualifies = (
                    include
                    and result == 'W'
                    and own - opp >= 5
                    and quit_inning <= 2
                    and standout is not None
                )

                if qualifies:
                    st.success(
                        '🔥 Forced early quit! This performance qualifies '
                        'for our proposed upgrade challenge.'
                    )
                else:
                    st.caption(
                        'Early-quit qualification requires Include scores, '
                        'a win, a lead of 5+ runs, inning 1 or 2, '
                        'and a standout player.'
                    )

                quit_note = (
                    f"Opponent quit in inning {int(quit_inning)}."
                )
                if include:
                    quit_note += f" Score: {int(own)}–{int(opp)}."
                if standout:
                    quit_note += f" Standout: {names[standout]}."
                if qualifies:
                    quit_note += ' Forced early quit qualification met.'

                notes = (notes.strip() + '\n' + quit_note).strip()

            lines=stat_fields(repo,fid,run['roster_ids'],'entry:'+run['id'])
            st.caption('H means all hits, including doubles, triples, and home runs.')

            stat_errors = []
            for row in lines:
                player = repo.get('players', row['player_id'])
                try:
                    validate_line(player['kind'], row['line'])
                except RuleError as exc:
                    stat_errors.append(f"{player['name']}: {exc}")

            for error in stat_errors:
                st.error(error)

            st.caption('Checks update when you press Enter or leave a cell. Finish the row before reviewing.')

            if st.button('Review game',type='primary',disabled=bool(stat_errors)):
                st.session_state[key]=dict(
                    request_id=uid(),
                    result=result,
                    opponent=opponent,
                    date=str(played),
                    team_score=int(own) if include else None,
                    opponent_score=int(opp) if include else None,
                    notes=notes,
                    lines=lines
                )
                st.rerun()

    else:
        import pandas as pd

        draft = st.session_state[key]
        st.subheader('Review and edit before saving')
        st.caption(
            'Edit a number below, then press Enter or click outside its cell. '
            'H means all hits, including doubles, triples, and home runs.'
        )
        st.write({
            k: v for k, v in draft.items()
            if k not in ['request_id', 'lines']
        })

        edited_lines = []
        errors = []

        for row in draft['lines']:
            player = repo.get('players', row['player_id'])
            st.write(player['name'])

            edited = st.data_editor(
                pd.DataFrame([row['line']]),
                key='review_stats:' + draft['request_id'] + ':' + row['player_id'],
                hide_index=True,
                width='stretch',
                num_rows='fixed',
                column_config={
                    field: st.column_config.NumberColumn(
                        'H · total hits' if field == 'h' else field,
                        min_value=0,
                        step=1,
                    )
                    for field in row['line']
                },
            )

            line = {
                field: None if pd.isna(value) else value
                for field, value in edited.to_dict('records')[0].items()
            }
            edited_lines.append(dict(row, line=line))

            try:
                validate_line(player['kind'], line)
            except (RuleError, ValueError, OverflowError) as exc:
                details = ''
                if player['kind'] == 'hitter':
                    details = (
                        f" Entered: AB={line.get('ab', 0)}, H={line.get('h', 0)},"
                        f" 2B={line.get('doubles', 0)}, 3B={line.get('triples', 0)},"
                        f" HR={line.get('hr', 0)}."
                    )
                errors.append(
                    f"{player['name']}: {str(exc).rstrip('.')}.{details}"
                )

        draft['lines'] = edited_lines

        for error in errors:
            st.error(error)

        if errors:
            st.info(
                'Your game has not been saved. Correct the player stats '
                'above; the other entries stay in place.'
            )

        a, b = st.columns(2)

        if a.button(
            'Confirm and save once',
            type='primary',
            disabled=bool(errors),
        ):
            try:
                record_game(repo, fid, **dict(draft, lines=edited_lines))
            except RuleError as exc:
                st.error(str(exc))
                st.info(
                    'Nothing was saved. You can continue editing the stats above.'
                )
            else:
                del st.session_state[key]
                st.session_state['last_saved_game'] = draft['request_id']
                st.rerun()

        if b.button('Discard draft'):
            del st.session_state[key]
            st.rerun()

    if st.session_state.get('last_saved_game'):
        st.success('Game saved. Your record and stats have been updated.')
        navigate('Return to dashboard','Dashboard')


def correction(repo,f):
    games=repo.list('games',f['id'])
    if not games:
        return

    st.subheader('Administrative game / stats correction')
    labels={
        g['id']:f"Run {repo.get('runs',g['run_id'])['number']} · Game {g['number']} · {g['result']}"
        for g in games
    }
    gid=st.selectbox('Game',list(labels),format_func=labels.get)
    game=repo.get('games',gid)
    run=repo.get('runs',game['run_id'])

    st.caption(
        'Stats corrections are always audited. Outcome edits are allowed '
        'only for the latest current-run game before dependent wheels '
        'or offseason actions.'
    )

    with st.form('correct:'+gid):
        outcome=st.selectbox(
            'Corrected result',
            ['W','L'],
            index=0 if game['result']=='W' else 1
        )
        lines=stat_fields(
            repo,
            f['id'],
            run['roster_ids'],
            'correct:'+gid,
            [
                s for s in repo.list('stats',f['id'],run['id'])
                if s['game_id']==gid
            ]
        )
        reason=st.text_input('Correction reason (required)')
        confirmed=st.checkbox(
            'I confirm replacement of this game’s stat lines.'
        )

        if st.form_submit_button('Apply audited correction') and confirmed:
            correct_game(repo,f['id'],gid,lines,reason,outcome)
            st.rerun()
