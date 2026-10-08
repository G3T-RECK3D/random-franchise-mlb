import streamlit as st
from models.domain import AREAS,POSITIONS
from services.roster_service import locked,add_player,arrange,swap,remove_player
from services.import_export import export_roster,import_roster
from services.roster_validator import validate
from services.franchise_service import audit
from ui.common import table,badges
from ui.forms import player_fields

def render(repo,f):
    fid=f['id'];players=repo.list('players',fid)
    is_locked=locked(repo,fid)
    if is_locked:st.info('Active run: lineup, bench, positions, rotation, and bullpen arrangements are available. New cards, call-ups, and removals wait until offseason.')
    for area in AREAS:
        with st.expander(area.title(),expanded=area in ['lineup','bench']):
            table([{'Player':p['name'],'Card':p['version'],'OVR':p['ovr'],'Position':p['position'],'Order':p['order'],
                    'Eligibility':p['eligibility'],'Status':badges(repo,fid,p)} for p in sorted(players,key=lambda p:p['order']) if p['area']==area])
    if players:
        ids=[p['id'] for p in players];labels={p['id']:p['name']+' · '+p['area'] for p in players}
        with st.form('arrange'):
            st.subheader('Arrange one player')
            pid=st.selectbox('Player',ids,format_func=labels.get)
            a,b,c=st.columns(3)
            area=a.selectbox('Destination area',AREAS[:-1])
            pos=b.selectbox('Assigned position',POSITIONS)
            order=c.number_input('Batting order / role priority',1,30,1)
            if st.form_submit_button('Save arrangement'):
                arrange(repo,fid,pid,area,pos,int(order));st.rerun()
        with st.form('swap'):
            st.subheader('Swap two assignments')
            first=st.selectbox('First player',ids,format_func=labels.get)
            second=st.selectbox('Second player',ids,format_func=labels.get)
            st.caption('Both destination positions must be legal. Use this for starter/bench swaps and order changes.')
            if st.form_submit_button('Swap assignments'):
                swap(repo,fid,first,second);st.rerun()
        with st.form('eligibility'):
            st.subheader('Update Event eligibility and notes')
            pid=st.selectbox('Card to verify',ids,format_func=labels.get)
            value=st.selectbox('Eligibility',['legal','illegal','unknown'])
            note=st.text_input('Verification note')
            if st.form_submit_button('Update eligibility'):
                with repo.transaction():
                    p=repo.get('players',pid);before=dict(p);p.update(eligibility=value,notes=note)
                    repo.put('players',p);audit(repo,fid,'eligibility',before,p,note or 'Manual eligibility check')
                st.rerun()
    if not is_locked:
        with st.expander('Add a card'):
            with st.form('new_player'):
                data=player_fields('new_')
                if st.form_submit_button('Add card'):
                    add_player(repo,fid,data);st.rerun()
        if players:
            with st.form('remove'):
                st.subheader('DFA / demote')
                pid=st.selectbox('Removal target',ids,format_func=labels.get)
                destination=st.selectbox('Destination',['dfa','minors'])
                confirm=st.checkbox('I confirm this offseason removal.')
                if st.form_submit_button('Apply removal') and confirm:
                    remove_player(repo,fid,pid,destination);st.rerun()
        upload=st.file_uploader('Import additional cards (CSV / JSON)',type=['csv','json'])
        confirmed=st.checkbox('Import appends cards; I have checked for duplicates.')
        if upload and confirmed and st.button('Import cards'):
            import_roster(repo,fid,upload.getvalue().decode('utf-8-sig'),upload.name.rsplit('.',1)[-1]);st.rerun()
    a,b=st.columns(2)
    a.download_button('Export roster JSON',export_roster(repo,fid),'roster.json','application/json')
    b.download_button('Export roster CSV',export_roster(repo,fid,'csv'),'roster.csv','text/csv')
    st.subheader('Roster check')
    result=validate(repo,fid)
    if result.valid:st.success('Roster composition and configured eligibility checks pass.')
    else:
        for error in result.errors:st.warning(error)
