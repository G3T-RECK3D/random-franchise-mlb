from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from repositories.sqlite import SQLiteRepository
from services.demo import load_demo

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('page',['app.py']+[str(p.relative_to(ROOT)) for p in sorted((ROOT/'pages').glob('*.py'))])
def test_pages_load_without_exception(tmp_path,monkeypatch,page):
    path=tmp_path/'ui.db';monkeypatch.setenv('RANDOM_FRANCHISE_DB',str(path))
    repo=SQLiteRepository(path);load_demo(repo);repo.close()
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=15).run()
    if page != 'app.py':
        app.switch_page(page).run()
    assert not app.exception,[x.message for x in app.exception]


def test_home_can_create_demo(tmp_path,monkeypatch):
    monkeypatch.setenv('RANDOM_FRANCHISE_DB',str(tmp_path/'ui.db'))
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    next(b for b in app.button if b.label=='Load Demo Franchise').click().run()
    assert not app.exception
    repo=SQLiteRepository(tmp_path/'ui.db')
    assert len(repo.list('franchises'))==1
    assert len(repo.list('players'))==27
    repo.close()

@pytest.mark.parametrize('state',['SETUP','AWAITING_WHEEL','RUN_ENDED','SELECTING_RUN_MVP','PROCESSING_ELIMINATION','PROCESSING_MELTDOWN','RESOLVING_BANKED_MOVES','ROSTER_RECONSTRUCTION','ROSTER_VALIDATION','READY_FOR_NEXT_RUN'])
def test_workflow_pages_for_each_state(tmp_path,monkeypatch,state):
    from services.game_engine import enqueue
    path=tmp_path/'states.db';monkeypatch.setenv('RANDOM_FRANCHISE_DB',str(path))
    repo=SQLiteRepository(path);fid=load_demo(repo);f=repo.get('franchises',fid)
    f['state']=state
    if state not in ['SETUP','AWAITING_WHEEL']:
        run=repo.get('runs',f['current_run']);run.update(wins=0,losses=2,ended_at='2026-10-08T00:00:00Z');repo.put('runs',run)
    if state=='AWAITING_WHEEL':enqueue(f,'front_office','ui test')
    repo.put('franchises',f);repo.close()
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    for page in ['pages/1_Dashboard.py','pages/4_Wheel_Room.py','pages/5_Banked_Moves.py','pages/6_Offseason.py','pages/9_Settings.py']:
        app.switch_page(page).run()
        assert not app.exception,[x.message for x in app.exception]


def test_review_save_and_hot_seat_ui(tmp_path,monkeypatch):
    path=tmp_path/'flow.db';monkeypatch.setenv('RANDOM_FRANCHISE_DB',str(path))
    repo=SQLiteRepository(path);load_demo(repo);repo.close()
    app=AppTest.from_file(str(ROOT/'app.py')).run().switch_page('pages/3_Game_Entry.py').run()
    next(s for s in app.selectbox if s.label=='Result').select('L')
    next(b for b in app.button if b.label=='Review game').click().run()
    next(b for b in app.button if b.label=='Confirm and save once').click().run()
    assert not app.exception
    repo=SQLiteRepository(path);fid=repo.list('franchises')[0]['id']
    assert len(repo.list('games',fid))==1
    repo.close()
    app.switch_page('pages/4_Wheel_Room.py').run()
    next(b for b in app.button if b.label=='Spin required wheel').click().run()
    assert not app.exception
