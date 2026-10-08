import streamlit as st
from services.stat_engine import aggregate
from ui.common import table

def render(repo,f):
    fid=f['id'];runs=repo.list('runs',fid);games=repo.list('games',fid);players=repo.list('players',fid)
    ended=[r for r in runs if r['ended_at']]
    a,b,c=st.columns(3)
    rank=lambda r:(r['wins'],-r['losses'])
    a.metric('Best run',f"{max(ended,key=rank)['wins']}–{max(ended,key=rank)['losses']}" if ended else '—')
    b.metric('Worst run',f"{min(ended,key=rank)['wins']}–{min(ended,key=rank)['losses']}" if ended else '—')
    streak=best=0
    for g in games:
        streak=streak+1 if g['result']=='W' else 0;best=max(best,streak)
    c.metric('Longest win streak',best)
    st.subheader('Event runs')
    table([{'Run':r['number'],'Event':r['event'],'W':r['wins'],'L':r['losses'],'Start':r['started_at'],'End':r['ended_at'],
            'MVP':repo.get('players',r['mvp'])['name'] if r['mvp'] else ''} for r in runs])
    st.subheader('Franchise leaders')
    hitter=sorted([{'Player':p['name'],**aggregate(repo,fid,p)} for p in players if p['kind']=='hitter'],key=lambda p:p['h'],reverse=True)
    pitcher=sorted([{'Player':p['name'],**aggregate(repo,fid,p)} for p in players if p['kind']=='pitcher'],key=lambda p:p['so'],reverse=True)
    table(hitter[:5]);table(pitcher[:5])
    st.subheader('Longest-tenured cards')
    table([{'Player':p['name'],'Acquired':p['acquired_at'],'Status':p['area']} for p in sorted(players,key=lambda p:p['acquired_at'])[:10]])
    for title,key in [('Games','games'),('Rewards and milestones','rewards'),('Roster changes and corrections','corrections'),
                      ('Banked rewards and punishments','moves'),('Franchise Tags','tags'),('Immutable wheel audit','spins'),('Roster snapshots','snapshots')]:
        with st.expander(title):
            for row in repo.list(key,fid):st.json(row,expanded=False)
