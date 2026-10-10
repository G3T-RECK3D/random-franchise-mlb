import hmac
import os
from pathlib import Path
import streamlit as st
from models.domain import RuleError, State
from repositories.postgres import PostgresRepository
from services.roster_service import locked

ROOT = Path(__file__).resolve().parents[1]
PAGE_PATHS = {'Dashboard':'pages/1_Dashboard.py','Roster Manager':'pages/2_Roster_Manager.py',
    'Game Entry':'pages/3_Game_Entry.py','Wheel Room':'pages/4_Wheel_Room.py','Banked Moves':'pages/5_Banked_Moves.py',
    'Offseason':'pages/6_Offseason.py','Player Stats':'pages/7_Player_Stats.py','Franchise History':'pages/8_Franchise_History.py',
    'Settings':'pages/9_Settings.py','Creator OBS View':'pages/10_Creator_OBS_View.py'}

def repo_path():
    return os.environ.get('RANDOM_FRANCHISE_DB', str(ROOT/'data'/'random_franchise.db'))

def authorize():
    password = os.environ.get('RANDOM_FRANCHISE_PASSWORD', '')
    try:
        password = st.secrets.get('app_password', password)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        pass
    if password and not st.session_state.get('authenticated'):
        typed = st.text_input('App password', type='password')
        if st.button('Unlock'):
            if hmac.compare_digest(typed, password):
                st.session_state['authenticated'] = True
                st.rerun()
            st.error('Incorrect password.')
        st.stop()

def context(title, obs=False):
    st.set_page_config(page_title='Random Franchise · '+title,page_icon='⚾',layout='wide')
    authorize()
    repo = PostgresRepository(st.secrets['postgres'])
    rows = repo.list('franchises')
    if not obs:
        st.sidebar.title('⚾ Random Franchise')
    if not rows:
        return repo, None
    ids = [r['id'] for r in rows]
    if st.session_state.get('active_franchise_id') not in ids:
        previous = st.session_state.get('selected_franchise')
        st.session_state['active_franchise_id'] = (
            previous if previous in ids else ids[0]
        )

    def remember_franchise():
        st.session_state['active_franchise_id'] = (
            st.session_state['_franchise_selector']
        )

    st.session_state['_franchise_selector'] = (
        st.session_state['active_franchise_id']
    )
    chosen = st.sidebar.selectbox(
        'Franchise',
        ids,
        format_func=lambda identifier: next(
            row['name'] for row in rows if row['id'] == identifier
        ),
        key='_franchise_selector',
        on_change=remember_franchise,
    )
    f = repo.get('franchises',chosen)
    if not obs:
        st.title(title)

        run = (
            repo.get('runs', f['current_run'])
            if f['current_run'] else None
        )
        season_id = (
            run.get('season_id') if run else None
        ) or f.get('current_season')
        season = (
            repo.get('seasons', season_id)
            if season_id else None
        )

        roster_status = (
            '🔒 Roster locked'
            if locked(repo, chosen) else 'Roster unlocked'
        )
        st.caption(
            f"{f['name']} · {f['state']} · {roster_status}"
        )

        if season:
            st.markdown(
                f"**Season {season['number']} · {season['name']}**"
            )
        else:
            st.caption(f['event'])

        if run:
            week = run.get('week_number', run['number'])
            st.markdown(
                f"**Week {week} · {run['wins']}–{run['losses']}**"
            )
        elif season:
            st.caption('No week started yet.')
    return repo,f

def run_page(title, renderer, obs=False):
    repo,f=context(title,obs)
    try:
        if f:
            renderer(repo,f)
        else:
            st.info('Create a franchise or load the demo on the Home page.')
            st.page_link('app.py',label='Open Home')
    except RuleError as exc:
        st.error(str(exc))
    finally:
        repo.close()

def navigate(label,key):
    st.page_link(PAGE_PATHS[key],label=label)

def table(rows):
    if rows:
        st.dataframe(rows,hide_index=True,width='stretch')
    else:
        st.caption('No entries yet.')

def badges(repo,fid,p):
    parts=[]
    if any(t['player_id']==p['id'] and t['active'] for t in repo.list('tags',fid)):parts.append('🔒 Franchise Tag')
    if p.get('protected'):parts.append('🛡 Protected')
    if p.get('hot_seat'):parts.append('⚠️ Hot Seat')
    if p['area']=='minors':parts.append('⬇️ Minors')
    if p['area']=='dfa':parts.append('❌ DFA')
    if any(c['player_id']==p['id'] and c['status']=='active' for c in repo.list('challenges',fid)):parts.append('🎯 Active Challenge')
    return ' · '.join(parts)
