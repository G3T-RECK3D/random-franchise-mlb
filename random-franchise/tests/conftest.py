import pytest
from repositories.sqlite import SQLiteRepository
from services.demo import load_demo

@pytest.fixture
def repo(tmp_path):
    r=SQLiteRepository(tmp_path/'test.db')
    yield r
    r.close()

@pytest.fixture
def demo(repo):
    return repo,load_demo(repo)
