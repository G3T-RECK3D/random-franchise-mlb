import json
import streamlit as st
from models.domain import AREAS,POSITIONS,RuleError,State
from services.roster_service import locked,add_player,arrange,swap,remove_player
from services.import_export import export_roster,import_roster
from services.roster_validator import validate
from services.franchise_service import audit
from ui.common import table,badges
from ui.forms import player_fields


def apply_complete_roster(repo, fid, cards, outgoing_area):
    """Reuse player IDs and replace active assignments in one transaction."""
    from services.roster_service import protected
    from services.roster_validator import legal_positions
    import unicodedata

    def name_key(value):
        text = unicodedata.normalize('NFD', value.strip().casefold())
        return ''.join(ch for ch in text if not unicodedata.combining(ch))

    if not isinstance(cards, list) or not cards:
        raise RuleError('Upload a JSON list of player cards.')
    if outgoing_area not in ['minors', 'dfa']:
        raise RuleError('Select Minors or DFA for outgoing cards.')

    with repo.transaction():
        f = repo.get('franchises', fid)
        if locked(repo, fid):
            raise RuleError('Finish the active week before applying a complete roster.')
        if f.get('queue') or f['state'] not in [State.SETUP, State.READY, State.REBUILD, State.VALIDATION]:
            raise RuleError('Finish required wheels and banked moves before applying a complete roster.')
        before = repo.list('players', fid)
        plan = []
        identities = set()
        used_existing = set()
        for card in cards:
            if not isinstance(card, dict):
                raise RuleError('Every card must be a JSON object.')
            if not isinstance(card.get('name'), str) or not card['name'].strip():
                raise RuleError('Every card needs a player name.')
            if not isinstance(card.get('card_uuid'), str) or not card['card_uuid'].strip():
                raise RuleError('Every card needs its verified card_uuid for duplicate-safe matching.')
            if card.get('kind') not in ['hitter', 'pitcher']:
                raise RuleError('Every card needs a valid hitter/pitcher kind.')
            identity = (card['card_uuid'], card['kind'])
            if identity in identities:
                raise RuleError('The JSON contains the same card twice: ' + card['name'])
            identities.add(identity)
            if type(card.get('ovr')) is not int or not 0 <= card['ovr'] <= 99:
                raise RuleError('Every card needs an integer OVR from 0 to 99.')
            if card.get('primary') not in POSITIONS or not isinstance(card.get('secondary'), list) or any(p not in POSITIONS for p in card['secondary']):
                raise RuleError('Invalid primary/secondary positions for ' + card['name'])
            area = card.get('area')
            if area not in ['lineup', 'bench', 'rotation', 'bullpen']:
                raise RuleError('A complete roster contains only active roster areas.')
            if type(card.get('order')) is not int or not 1 <= card['order'] <= 30:
                raise RuleError('Use positive integer order numbers from 1 to 30.')
            if card.get('position') not in POSITIONS:
                raise RuleError('Invalid assigned position for ' + card['name'])
            if card.get('eligibility') != 'legal':
                raise RuleError('Verify Event eligibility for every card before applying.')
            if area in ['lineup', 'bench'] and card['kind'] != 'hitter':
                raise RuleError('Lineup and bench entries must be hitters.')
            if area == 'lineup' and (card['position'] not in legal_positions(card) or not 1 <= card['order'] <= 9):
                raise RuleError('Illegal lineup position/order for ' + card['name'])
            if area in ['rotation', 'bullpen']:
                role = 'SP' if area == 'rotation' else 'RP'
                if card['kind'] != 'pitcher' or card['position'] != role or role not in legal_positions(card):
                    raise RuleError('Illegal pitching role for ' + card['name'])

            matches = [p for p in before if p.get('card_uuid') == card['card_uuid'] and p['kind'] == card['kind']]
            if len(matches) > 1:
                raise RuleError('Multiple existing entries match ' + card['name'] + '. Resolve the duplicate first; no changes were saved.')
            if matches:
                player = matches[0]
                if name_key(player['name']) != name_key(card['name']) or player['ovr'] != card['ovr']:
                    raise RuleError('Existing card identity disagrees with the JSON: ' + card['name'])
            else:
                # Older manually entered cards may lack UUIDs. Match only when unambiguous.
                legacy = [p for p in before if not p.get('card_uuid') and name_key(p['name']) == name_key(card['name']) and p['kind'] == card['kind'] and p['ovr'] == card['ovr']]
                if len(legacy) > 1:
                    raise RuleError('Multiple older entries match ' + card['name'] + '. Resolve the duplicate first.')
                player = legacy[0] if legacy else None
                if player and player.get('series') and player['series'].strip().casefold() != str(card.get('series', '')).strip().casefold():
                    raise RuleError('Confirm the older card series for ' + card['name'] + ' before importing.')
            if player:
                if player['id'] in used_existing:
                    raise RuleError('Two incoming cards matched the same existing player.')
                used_existing.add(player['id'])
            plan.append((card, player))

        lineup = [c for c in cards if c['area'] == 'lineup']
        if len(lineup) != 9 or sorted(c['order'] for c in lineup) != list(range(1, 10)):
            raise RuleError('Include nine lineup hitters with each order number 1–9 exactly once.')
        if len({c['position'] for c in lineup}) != 9:
