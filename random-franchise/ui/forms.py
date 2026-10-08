import pandas as pd
import streamlit as st
from models.domain import POSITIONS, AREAS
from services.stat_engine import HITTER, PITCHER


def player_fields(prefix='',area_default='minors'):
    a,b,c=st.columns(3)
    name=a.text_input('Player name',key=prefix+'name')
    version=b.text_input('Card/version',value='Base',key=prefix+'version')
    ovr=c.number_input('OVR',0,99,75,key=prefix+'ovr')
    a,b,c=st.columns(3)
    kind=a.selectbox('Type',['hitter','pitcher'],key=prefix+'kind')
    primary=b.selectbox('Primary position',POSITIONS,key=prefix+'primary')
    secondary=c.multiselect('Secondary positions',POSITIONS,key=prefix+'secondary')
    a,b,c=st.columns(3)
    area=a.selectbox('Roster area',AREAS,index=AREAS.index(area_default),key=prefix+'area')
    position=b.selectbox('Assigned position',POSITIONS,key=prefix+'position')
    order=c.number_input('Order / role priority',1,30,1,key=prefix+'order')
    a,b,c=st.columns(3)
    team=a.text_input('Team (optional)',key=prefix+'team')
    series=b.text_input('Series (optional)',key=prefix+'series')
    eligibility=c.selectbox('Event eligibility',['unknown','legal','illegal'],key=prefix+'eligibility')
    a,b=st.columns(2)
    bat=a.selectbox('Bats',['','L','R','S'],key=prefix+'bat')
    throw=b.selectbox('Throws',['','L','R'],key=prefix+'throw')
    notes=st.text_area('Notes',key=prefix+'notes')
    return dict(name=name,version=version,ovr=int(ovr),kind=kind,primary=primary,secondary=secondary,area=area,
                position=position,order=int(order),team=team,series=series,eligibility=eligibility,bat=bat,throw=throw,notes=notes)


def stat_fields(repo, fid, roster_ids, prefix, existing=None):
    old={s['player_id']:s for s in (existing or [])}
    output=[]
    for kind,keys in [('hitter',HITTER),('pitcher',PITCHER)]:
        players=[repo.get('players',pid) for pid in roster_ids]
        players=[p for p in players if p and p['kind']==kind]
        players.sort(
            key=lambda p: (
                {
                    'lineup': 0,
                    'bench': 1,
                    'rotation': 0,
                    'bullpen': 1,
                }.get(p['area'], 2),
                p.get('order', 99),
                p['name'],
                p['id'],
            )
        )
        rows=[]
        for p in players:
            prior=old.get(p['id'],{})
            row={'player_id':p['id'],'Player':p['name'],'Played':bool(prior)}
            row.update({key:prior.get('line',{}).get(key,1 if key=='games' else 0) for key in keys})
            if kind=='pitcher':
                row.update(no_hitter=prior.get('flags',{}).get('no_hitter',False),perfect_game=prior.get('flags',{}).get('perfect_game',False))
            rows.append(row)
        st.subheader(kind.title()+' stat lines')
        st.caption('Check Played for participants. PA includes AB + BB + HBP + SF. Pitcher innings use outs: 1 inning = 3 outs.')
        if rows:
            edited=st.data_editor(pd.DataFrame(rows),key=prefix+kind,hide_index=True,width='stretch',disabled=['Player','player_id'],
                column_config={'player_id':None,**{key:st.column_config.NumberColumn(key,min_value=0,step=1) for key in keys}})
            for row in edited.to_dict('records'):
                if row['Played']:
                    output.append(dict(player_id=row['player_id'],line={key:int(row[key]) for key in keys},
                        flags={flag:bool(row.get(flag,False)) for flag in ['no_hitter','perfect_game']}))
    st.caption('No-hitter / perfect-game flags are creator-confirmed complete-game feats; verify all in-game requirements before checking them.')
    return output
