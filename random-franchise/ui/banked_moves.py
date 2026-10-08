import json
import streamlit as st
from services.offseason_service import resolve_move
from services.roster_service import locked
from models.domain import State
from ui.common import table,navigate

def render(repo,f):
    moves=repo.list('moves',f['id'])
    table([{'ID':m['id'],'Source':m['source'],'Run':repo.get('runs',m['run_id'])['number'] if m.get('run_id') else '',
        'Game':repo.get('games',m['game_id'])['number'] if m.get('game_id') else '',
        'Type':m['type'],'Description':m['description'],'Constraints':json.dumps(m.get('constraints',{})),
        'Status':m['status'],'Critical':m.get('critical',False),'Timing':'Offseason only'} for m in moves])
    if locked(repo,f['id']):st.info('Moves are banked until the run ends.');return
    if f['state'] not in [State.MOVES,State.REBUILD,State.VALIDATION]:
        st.info('Confirm Run MVP and complete required offseason wheels first.');navigate('Continue offseason','Offseason');return
    pending=[m for m in moves if m['status'] in ['pending','deferred']]
    if not pending:return
    mid=st.selectbox('Move to resolve',[m['id'] for m in pending],format_func=lambda i:next(m['description'] for m in pending if m['id']==i))
    m=repo.get('moves',mid)
    players=repo.list('players',f['id']);ids=[p['id'] for p in players]
    labels={p['id']:p['name']+' · '+p['area'] for p in players}
    st.info(json.dumps(m.get('constraints',{}),indent=2))
    with st.form('resolve:'+mid):
        action=st.selectbox('Resolution',['resolved','deferred','canceled'])
        target=st.selectbox('Target / replacement / tag recipient (if needed)',[None]+ids,
                            index=(ids.index(m['target'])+1) if m.get('target') in ids else 0,
                            format_func=lambda i:labels.get(i,'Use original target / no target'))
        replacement=st.selectbox('Replace existing tag holder (only at tag cap)',[None]+ids,format_func=lambda i:labels.get(i,'No replacement'))
        cancel_id=None
        if m['type'] in ['cancel_elimination', 'save_dfa']:
            eligible=[x for x in moves if x['run_id']==m['run_id'] and x['status']=='pending' and x['type'] in (['dfa'] if m['type']=='save_dfa' else ['dfa','demote','trade'])]
            cancel_id=st.selectbox('Consequence to cancel',[None]+[x['id'] for x in eligible],format_func=lambda i:next((x['description'] for x in eligible if x['id']==i),'Choose a consequence'))
        new=None
        if m['type'] == 'upgrade':
            player = repo.get('players', m['target'])
            st.info(
                'Upgrade ' + player['name']
                + ' to the next available higher-rated Event-legal card. '
                'Keep the name and player type unchanged; update the card details.'
            )
            template = {
                field: player.get(field, '')
                for field in [
                    'name', 'version', 'ovr', 'primary', 'secondary',
                    'kind', 'team', 'series', 'bat', 'throw', 'eligibility',
                ]
            }
            incoming = st.text_area(
                'Upgraded card JSON',
                value=json.dumps(template, indent=2),
                height=300,
            )
            next_card_confirmed = st.checkbox(
                'I verified this is the next available higher-rated '
                'Event-legal card of this player.'
            )
        elif m['type'] in ['acquire','trade']:
            st.caption('Enter incoming cards as JSON. Confirm the wheel’s external constraints yourself. Cards default to minors until arranged.')
            template=[dict(name='New Card',version='Base',ovr=80,primary='CF',secondary=['LF','RF'],kind='hitter',area='minors',position='CF',order=1,eligibility='legal')]
            incoming=st.text_area('Incoming card(s) JSON',value=json.dumps(template,indent=2),height=230)
        notes=st.text_area('Resolution notes / external-constraint verification')
        confirm=st.checkbox('I confirm the selected action, targets, and qualifying incoming cards.')
        if st.form_submit_button('Apply offseason resolution',type='primary'):
            if m['type'] in ['acquire','trade','upgrade'] and action=='resolved':
                if m['type'] == 'upgrade' and not next_card_confirmed:
                    st.error('Confirm the next available legal card first.')
                    return
                try:
                    parsed=json.loads(incoming)
                    new=parsed[0] if m['type'] in ['trade','upgrade'] and isinstance(parsed,list) and len(parsed)==1 else parsed
                except (ValueError,IndexError):
                    st.error('Incoming JSON is invalid.');return
            resolve_move(repo,f['id'],mid,action,notes,target,new,replacement,confirm,cancel_id);st.rerun()
