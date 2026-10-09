import streamlit as st
from ui.common import run_page


def render(repo, f):
    st.subheader('⚾ On the Field')
    st.caption('Your franchise lineup view is coming next.')
    st.page_link(
        'pages/2_Roster_Manager.py',
        label='Edit roster and batting order',
        icon='✏️',
    )


run_page('Lineup', render, obs=False)
