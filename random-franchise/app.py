import streamlit as st
from ui.common import context
from services.franchise_service import create_franchise
from services.demo import load_demo
from models.domain import RuleError
from services.backup_service import restore_empty

repo,f=context('Home')
try:
    st.title('⚾ Random Franchise')
    st.markdown('Your Event challenge, one run at a time. Record games, spin wheels, bank upgrades, and rebuild after your second loss.')
    if f:
        st.page_link('pages/1_Dashboard.py',label='Open franchise dashboard',icon='▶️')
    with st.form('create'):
        st.subheader('Create a franchise')
        name=st.text_input('Franchise name')
        event=st.text_input('Event name',value='My Event')
        if st.form_submit_button('Create franchise'):
            fid=create_franchise(repo,name,event)
            st.session_state['selected_franchise']=fid
            st.rerun()
    if st.button('Load Demo Franchise',type='primary'):
        st.session_state['selected_franchise']=load_demo(repo)
        st.rerun()
    if not f:
        with st.expander('Restore a full backup into this empty installation'):
            backup = st.file_uploader('SQLite backup', type=['db'])
            confirmed = st.checkbox('Restore this backup into the empty installation.')
            if backup and confirmed and st.button('Restore complete backup'):
                restore_empty(repo, backup.getvalue())
                st.rerun()
    st.caption('The demo contains fictional cards. Set up or import your real roster manually. Export backups from Settings regularly.')
except RuleError as exc:
    st.error(str(exc))
finally:
    repo.close()
