import streamlit as st
from services.stat_engine import aggregate
from ui.common import table,badges

def render(repo,f):
    players=repo.list('players',f['id'])
    if not players:st.info('Add players first.');return
    runs=repo.list('runs',f['id'])
    scope=st.selectbox('Statistics scope',['Franchise lifetime','Current Event run','Individual game'])
    rid=f.get('current_run') if scope=='Current Event run' else None
    gid=None
    games=repo.list('games',f['id'])
    if scope=='Individual game':
        if not games:st.info('No games entered.');return
        labels={g['id']:f"Run {repo.get('runs',g['run_id'])['number']} · Game {g['number']}" for g in games}
        gid=st.selectbox('Game',list(labels),format_func=labels.get)
    for kind in ['hitter','pitcher']:
        st.subheader(kind.title()+'s')
        table([{'Player':p['name'],**aggregate(repo,f['id'],p,rid,gid)} for p in players if p['kind']==kind])
    st.subheader('Player profile')
    labels={p['id']:p['name'] for p in players}
    pid=st.selectbox('Player',list(labels),format_func=labels.get)
    p=repo.get('players',pid)
    st.write(badges(repo,f['id'],p));st.json(p)
