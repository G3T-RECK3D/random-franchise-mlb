import html
import math
import streamlit as st
import streamlit.components.v1 as components
from services.wheel_engine import current_job,available,spin,continue_spin,retry_impossible_branch
from services.franchise_service import settings
from ui.common import navigate

def visual(result,reduced):
    options=result['available']
    if not options:return
    count=len(options);angle=360/count
    selected=next((i for i,w in enumerate(options) if w['id']==result['result']['id']),0)
    pieces=[]
    colors=['#42e2ae','#277da1','#f9c74f','#f9844a','#9b5de5']
    for i,w in enumerate(options):
        a,b=math.radians(i*angle-90),math.radians((i+1)*angle-90)
        x1,y1=180+155*math.cos(a),180+155*math.sin(a)
        x2,y2=180+155*math.cos(b),180+155*math.sin(b)
        if count==1:pieces.append('<circle cx="180" cy="180" r="155" fill="#42e2ae"/>')
        else:pieces.append(f'<path d="M180 180 L{x1} {y1} A155 155 0 {int(angle>180)} 1 {x2} {y2} Z" fill="{colors[i%5]}" stroke="#0a1421"/>')
        mid=math.radians((i+.5)*angle-90);x,y=180+110*math.cos(mid),180+110*math.sin(mid)
        pieces.append(f'<text x="{x}" y="{y}" fill="#07111e" text-anchor="middle" font-size="12">{i+1}</text>')
    rotation=-(selected+.5)*angle+1440
    animation='' if reduced else 'animation:land 3s cubic-bezier(.14,.62,.19,1) forwards;'
    svg=''.join(pieces)
    components.html(f'''<style>body{{background:#0a1421;color:white;text-align:center;font-family:sans-serif}}svg{{width:340px;transform:rotate({rotation}deg);{animation}}}@keyframes land{{from{{transform:rotate(0deg)}}to{{transform:rotate({rotation}deg)}}}}@media(prefers-reduced-motion:reduce){{svg{{animation:none!important}}}}</style><div style="font-size:28px">▼</div><svg viewBox="0 0 360 360">{svg}</svg><div>Selected wedge {selected+1}: {html.escape(result['result']['text'])}</div>''',height=420)


def wheel_preview(options):
    if not options:
        return

    colors = ['#ff334f', '#ffb703', '#34d399', '#60a5fa', '#a78bfa']
    angle = 360 / len(options)
    pieces = []

    for i, option in enumerate(options):
        color = colors[i % len(colors)]
        start = math.radians(i * angle - 90)
        end = math.radians((i + 1) * angle - 90)
        x1, y1 = 180 + 155 * math.cos(start), 180 + 155 * math.sin(start)
        x2, y2 = 180 + 155 * math.cos(end), 180 + 155 * math.sin(end)

        if len(options) == 1:
            pieces.append(
                f'<circle cx="180" cy="180" r="155" fill="{color}"/>'
            )
        else:
            pieces.append(
                f'<path d="M180 180 L{x1} {y1} '
                f'A155 155 0 {int(angle > 180)} 1 {x2} {y2} Z" '
                f'fill="{color}" stroke="#111827" stroke-width="3"/>'
            )

        middle = math.radians((i + 0.5) * angle - 90)
        x = 180 + 110 * math.cos(middle)
        y = 180 + 110 * math.sin(middle)
        pieces.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" '
            f'fill="#111827" font-size="20" font-weight="bold">'
            f'{i + 1}</text>'
        )

    components.html(
        '<div style="text-align:center;color:white;'
        'font-family:sans-serif;">'
        '<div style="font-size:28px;color:#ff334f;">▼</div>'
        '<svg viewBox="0 0 360 360" style="width:100%;max-width:340px;">'
        + ''.join(pieces)
        + '<circle cx="180" cy="180" r="34" fill="#111827" '
        'stroke="white" stroke-width="3"/>'
        '<text x="180" y="187" text-anchor="middle" '
        'fill="white" font-size="18" font-weight="bold">SPIN</text>'
        '</svg></div>',
        height=410,
    )
    st.caption(
        'Ready to spin. Wedge numbers match the list below; '
        'the configured weights determine the odds.'
    )
def render(repo,f):
    job=current_job(repo,f['id'])
    if not job:
        st.info('No wheel is due right now.');navigate('Next step on dashboard','Dashboard');return
    wheel=repo.get('wheels',f"{f['id']}:{job['wheel_id']}")
    st.subheader(wheel['display_name'])
    st.caption('Source: '+job['source'])
    if job.get('constraints'):st.info('Branch constraints: '+' → '.join(job['constraints']))
    cfg=settings(repo,f['id'])
    reduced=st.checkbox('Reduced motion / simple fallback',value=cfg['reduced_motion'])
    st.checkbox('Sound (placeholder; V1 has no audio)',value=False,disabled=True)
    result=repo.get('spins',job['id'])
    if not result:
        options=available(repo,f['id'],job)
        wheel_preview(options)
        with st.expander('Eligible wedges and weights'):
            st.dataframe([{'Wedge':w['text'],'Weight':w['weight']} for w in options],hide_index=True)
        if st.button('Spin required wheel',type='primary'):
            spin(repo,f['id'],job['id']);st.rerun()
    else:
        if not reduced:visual(result,reduced)
        st.success('Result: '+result['result']['text'])
        outcome = result['result']
        effect = outcome.get('effect', 'acquire')
        target = (
            repo.get('players', result['target'])
            if result.get('target') else None
        )

        if not outcome.get('follow_up') and effect in [
            'acquire', 'trade', 'dfa', 'demote'
        ]:
            with st.container(border=True):
                st.subheader('What this means')

                if effect == 'acquire':
                    quantity = outcome.get('quantity', 1)
                    st.write(
                        f'**Reward:** Add {quantity} Event-eligible '
                        'card(s) matching this wheel result.'
                    )
                    st.write(
                        '**Player choice:** Choose the incoming card yourself. '
                        'The displayed target does not apply to this reward.'
                    )
                    st.write(
                        '**Roster:** Your previous starter can stay on the '
                        'bench if roster limits allow.'
                    )
                else:
                    instructions = {
                        'trade': 'Trade away the selected player and add one incoming card.',
                        'dfa': 'Move the selected player to DFA.',
                        'demote': 'Move the selected player to minors.',
                    }
                    st.write('**Required action:** ' + instructions[effect])
                    if target:
                        st.write('**Selected player:** ' + target['name'])
                    if effect == 'trade':
                        st.write(
                            '**Incoming card:** Choose an Event-eligible card '
                            'that satisfies this result’s restrictions.'
                        )

                st.write(
                    '**Result instructions:** '
                    + outcome.get('description', outcome['text'])
                )
                branch = result.get('job', {}).get('constraints', [])
                if branch:
                    st.write('**Earlier wheel restrictions:** ' + ' → '.join(branch))
                st.write('**Timing:** Apply during offseason in Banked Moves.')
                st.caption(
                    'Click Continue with this result to bank it. '
                    'This does not change your roster immediately.'
                )
        else:
            with st.container(border=True):
                st.subheader('What this means')

                if outcome.get('follow_up'):
                    st.write(
                        '**Next step:** Continue to another wheel. '
                        'This result’s restrictions carry into that spin.'
                    )
                elif effect == 'challenge':
                    st.write('**Challenge:** ' + outcome['text'])
                    scopes = {
                        'next_game': 'Your next qualifying saved game.',
                        'next_run': 'Your next run.',
                        'run': 'This run.',
                    }
                    scope = outcome.get('scope', 'next_game')
                    st.write(
                        '**When it counts:** '
                        + scopes.get(scope, 'See the challenge instructions.')
                    )
                    if outcome.get('metric'):
                        st.write(
                            '**Goal:** '
                            + str(outcome.get('threshold', 1))
                            + ' ' + outcome['metric'].upper()
                        )
                        st.caption('Progress updates from saved game stats.')
                    else:
                        st.caption(
                            'This challenge requires evidence and manual '
                            'confirmation during offseason.'
                        )
                    rewards = {
                        'tag': 'Franchise Tag',
                        'protection': 'Player protection',
                        'upgrade': 'Card upgrade',
                    }
                    reward = outcome.get('reward', 'protection')
                    st.write('**Reward:** ' + rewards.get(reward, reward))
                elif effect == 'protect':
                    if 'Next Run' in outcome['text']:
                        st.write(
                            '**Reward:** Protection for next run. '
                            'Continue to bank it, then apply it during offseason.'
                        )
                    else:
                        st.write(
                            '**Reward:** Give the selected player temporary '
                            'protection from removal. Applied when you continue.'
                        )
                elif effect == 'unprotect':
                    st.write(
                        '**Consequence:** Remove the selected player’s '
                        'temporary protection when you continue.'
                    )
                elif effect == 'hot_seat':
                    st.write(
                        '**Consequence:** Mark the selected player for Hot Seat '
                        'targeting when you continue. This does not remove them.'
                    )
                elif effect == 'tag':
                    st.write(
                        '**Reward:** Grant the selected player a Franchise Tag '
                        'when you continue. If the tag cap is full, resolve '
                        'the replacement decision in Banked Moves during offseason.'
                    )
                elif effect == 'extra_spin':
                    st.write(
                        '**Reward:** Add extra spin(s) on this wheel '
                        'when you continue.'
                    )
                elif effect == 'arrangement':
                    st.write(
                        '**Required action:** Apply the arrangement in '
                        'Roster Manager, then check the confirmation below.'
                    )
                elif effect == 'none':
                    st.write('No roster change or reward is applied.')
                elif effect == 'deferred':
                    st.write(
                        'No eligible result was available. Continue to defer '
                        'this branch, or use the retry button if available.'
                    )
                else:
                    st.write(
                        '**Timing:** Continue to bank this result. '
                        'Review and resolve it during offseason in Banked Moves.'
                    )

                if target and not outcome.get('follow_up'):
                    st.write('**Selected player:** ' + target['name'])
                description = outcome.get('description')
                if description:
                    st.write('**Instructions:** ' + description)
        acknowledged=False
        if result['result']['effect']=='arrangement':
            st.info(result['result']['description'])
            navigate('Apply arrangement in Roster Manager','Roster Manager')
            acknowledged=st.checkbox('I applied this arrangement using existing cards and verified it is legal.')
        if result['result']['id'] == 'impossible' and job.get('parent_spin'):
            if st.button('Retry impossible child only (requires eligible options)'):
                retry_impossible_branch(repo, f['id'], job['id']); st.rerun()
        if st.button('Continue with this result',type='primary'):
            continue_spin(repo,f['id'],job['id'],acknowledged);st.rerun()
        st.caption('Result is persisted before display. Refreshing does not grant another spin.')
