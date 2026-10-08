import html
import streamlit as st
from services.wheel_engine import current_job

def render(repo,f):
    st.markdown('<style>[data-testid="stSidebar"],header,footer{display:none}.block-container{padding:1rem;max-width:1600px}</style>',unsafe_allow_html=True)
    fid=f['id'];run=repo.get('runs',f['current_run']) if f['current_run'] else None
    games=repo.list('games',fid);spins=repo.list('spins',fid);job=current_job(repo,fid)
    tags={t['player_id'] for t in repo.list('tags',fid) if t['active']}
    players=repo.list('players',fid)
    esc=html.escape
    values=[('EVENT RUN',f"{run['wins']} — {run['losses']}" if run else 'READY'),
      ('FRANCHISE',f"{sum(g['result']=='W' for g in games)} — {sum(g['result']=='L' for g in games)}"),
      ('CURRENT WHEEL',repo.get('wheels',f"{fid}:{job['wheel_id']}")['display_name'] if job else 'No wheel due'),
      ('LATEST RESULT',spins[-1]['result']['text'] if spins else '—'),
      ('HOT SEAT',', '.join(p['name'] for p in players if p.get('hot_seat')) or 'None'),
      ('FRANCHISE TAGS',', '.join(p['name'] for p in players if p['id'] in tags) or 'None'),
      ('ACTIVE CHALLENGE',' · '.join(c['description'] for c in repo.list('challenges',fid) if c['status']=='active') or 'None'),
      ('BANKED MOVES',str(sum(m['status'] in ['pending','deferred'] for m in repo.list('moves',fid))))]
    cells=''.join(f'<div class="tile"><div class="label">{esc(label)}</div><div class="value">{esc(value)}</div></div>' for label,value in values)
    st.markdown(f'''<style>.capture{{aspect-ratio:16/9;background:#0a1421;padding:30px;border:2px solid #42e2ae;border-radius:20px;box-sizing:border-box;overflow:hidden}}.capture h1{{font-size:38px;color:#42e2ae}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.tile{{background:#152638;padding:18px;border-radius:12px}}.label{{color:#42e2ae;font-size:14px;letter-spacing:2px}}.value{{font-size:27px;font-weight:bold;overflow-wrap:anywhere}}</style><section class="capture"><h1>⚾ {esc(f['name'])}</h1><div class="grid">{cells}</div></section>''',unsafe_allow_html=True)
    # Refreshing reads persistent data; no management operations exist on this page.
