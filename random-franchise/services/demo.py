from models.domain import now, uid
from services.franchise_service import create_franchise
from services.roster_service import add_player
from services.franchise_tag_service import grant
from services.game_engine import start_run
from services.challenge_service import create


def load_demo(repo):
    with repo.transaction():
        fid = create_franchise(repo, 'Cedar City Comets (Demo)', 'Open exhibition Event')
        positions = ['C','1B','2B','3B','SS','LF','CF','RF','DH']
        names = ['Alex Vale','River Stone','Jordan Pine','Casey Brook','Drew Summit','Morgan Lake','Taylor Reed','Riley Ash','Sam West']
        for i,(name,position) in enumerate(zip(names,positions),1):
            add_player(repo,fid,dict(name=name,ovr=79+i,primary=position,secondary=positions[:-1],kind='hitter',area='lineup',position=position,order=i,eligibility='legal'))
        for i in range(4):
            add_player(repo,fid,dict(name=f'Bench Prospect {i+1}',ovr=74+i,primary='CF',secondary=positions[:-1],kind='hitter',area='bench',position='CF',order=i+1,eligibility='legal'))
        for area,position,size in [('rotation','SP',5),('bullpen','RP',8)]:
            for i in range(size):
                add_player(repo,fid,dict(name=f'{area.title()} Ace {i+1}',ovr=78+i,primary=position,secondary=['SP','RP'],kind='pitcher',area=area,position=position,order=i+1,eligibility='legal'))
        add_player(repo,fid,dict(name='Jamie Orchard',primary='SS',secondary=['2B'],ovr=72,eligibility='legal'))
        first=repo.list('players',fid)[0]
        grant(repo,fid,first['id'],source='Demo franchise cornerstone')
        rid=start_run(repo,fid)
        create(repo,fid,rid,first['id'],'Get a hit in your next game','h',1)
        repo.put('moves',dict(id=uid(),franchise_id=fid,run_id=rid,game_id=None,type='acquire',source='demo',
            description='Demo: sign one legal free agent in offseason',constraints={'quantity':1},status='pending',critical=False,created_at=now()))
        return fid
