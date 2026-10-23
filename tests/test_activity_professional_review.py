"""Compatibilidad de la revisión profesional con filtros, recibos e historiales."""

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from analytics_service.activities import ACTIVITY_IDS, CATALOG_VERSION, select_activities
from analytics_service.child_offers import ChildOfferCoordinator, OfferEvidence, POLICY
from analytics_service.http import create_app
from analytics_service.settings import Settings
from recommendations import (
    ACTIVITY_CATALOG, ACTIVITY_MERGE_PREDECESSORS, ActivityEligibility,
    CHILD_ACTIVITY_INTRO_TEXT, RETIRED_ACTIVITY_IDS, recommend_activities,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / 'tests/fixtures/catalog_revision/base_1445056_fictitious.json').read_text(encoding='utf-8'))
REVISION = json.loads((ROOT / 'docs/activity_catalog/REVISION_PROFESIONAL_2026-10-23.json').read_text(encoding='utf-8'))
TOKEN = 'fictitious-professional-review-token'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}
MERGED_OLD_IDS = frozenset().union(*ACTIVITY_MERGE_PREDECESSORS.values())
MERGE_CASES = [(current, old) for current, old_ids in ACTIVITY_MERGE_PREDECESSORS.items() for old in sorted(old_ids)]


def restore_store(path, case):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
        db.execute('CREATE TABLE receipts (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, body TEXT NOT NULL)')
        db.execute('INSERT INTO state VALUES (1, ?)', (case['store']['state_body'],))
        db.executemany('INSERT INTO receipts VALUES (?, ?, ?)', case['store']['receipts'])


def store_rows(path):
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        return (db.execute('SELECT body FROM state WHERE id=1').fetchone()[0],
                db.execute('SELECT id, fingerprint, body FROM receipts ORDER BY id').fetchall())


def request(**changes):
    return {'request_id': 'fictitious-professional-selection', 'context': 'voluntary',
            'eligibility_state': 'known', 'eligibility': {}, **changes}


def test_recorded_source_hashes_and_all_activity_correspondences():
    assert len(ACTIVITY_CATALOG) == 16
    assert REVISION['catalog_version'] == CATALOG_VERSION
    assert REVISION['common_child_text'] == CHILD_ACTIVITY_INTRO_TEXT
    assert REVISION['clinical_approval_claim'] is False
    assert REVISION['child_effectiveness_validated'] is False
    assert REVISION['automatic_condition_to_filter_mapping'] is False
    hashes = {r['sha256'] for r in REVISION['sources']}
    assert hashes == {'7d76c1f11577e1c05c6f68ae220817cfbbdb008edc4d866cbb3c91a651a9917d',
                      'f7f9da6f8846bc3a123bee42532198eaec4fda510368f491113bd85c122d0f96'}
    assert {n for row in REVISION['activities'] for n in row['source_document_numbers']} == set(range(1, 19)) | {20}
    current = {a.activity_id: json.loads(json.dumps(asdict(a))) for a in ACTIVITY_CATALOG}
    assert {r['activity']['activity_id']: r['activity'] for r in REVISION['activities']} == current
    assert MERGED_OLD_IDS <= RETIRED_ACTIVITY_IDS
    assert not ACTIVITY_IDS & RETIRED_ACTIVITY_IDS
    assert set(BASE['policy']) == set(POLICY)
    assert BASE['policy'] == POLICY


@pytest.mark.parametrize('merged_id,old_id', MERGE_CASES)
def test_predecessor_exclusion_blocks_merged_activity_in_direct_and_http_selection(merged_id, old_id):
    other_ids = ACTIVITY_IDS - {merged_id}
    exclusions = sorted(other_ids | {old_id})
    rules = ActivityEligibility(excluded_activity_ids=tuple(exclusions))
    assert merged_id in rules.excluded_activity_ids
    assert recommend_activities('voluntary', eligibility=rules, n=30, random_seed=0) == []
    payload = request(eligibility={'excluded_activity_ids': exclusions})
    assert select_activities(payload)['status'] == 'no_eligible_activities'
    with TestClient(create_app(Settings(token=TOKEN))) as client:
        response = client.post('/v1/activities/select', json=payload, headers=HEADERS)
        assert response.status_code == 200
        assert response.json()['status'] == 'no_eligible_activities'
        assert response.json()['activities'] == []


def test_old_choice_counts_do_not_transfer_to_merged_identities():
    old_counts = {aid: 10000 for aid in MERGED_OLD_IDS}
    for seed in range(12):
        assert recommend_activities('voluntary', random_seed=seed, selected_activity_counts=old_counts) == recommend_activities('voluntary', random_seed=seed)


@pytest.mark.parametrize('case', BASE['cases'], ids=lambda c: c['case'])
def test_upgrade_reopens_old_stores_and_replays_original_http_receipts_without_writes(tmp_path, case):
    path = tmp_path / 'fictitious-before-upgrade.sqlite'
    restore_store(path, case)
    before = store_rows(path)
    settings = Settings(token=TOKEN, child_offers_enabled=True, child_offers_repository_path=path)
    for _ in range(2):
        with TestClient(create_app(settings)) as client:
            assert client.get('/health').status_code == 200
            for operation in case['operations']:
                if operation['kind'] == 'evaluate':
                    response = client.post('/v1/child-offers/evaluate', json={
                        'request_id': operation['request_id'], 'evidence': operation['evidence']}, headers=HEADERS)
                else:
                    response = client.post('/v1/child-offers/events', json={
                        'request_id': operation['request_id'], **operation['payload']}, headers=HEADERS)
                assert response.status_code == 200
                assert response.json() == {**operation['receipt'], 'replayed': True}
                assert response.json()['offer']['selection']['catalog_version'] == BASE['catalog_version']
            history = client.get('/v1/child-offers/profiles/' + case['profile_id'] + '/history', headers=HEADERS)
            assert history.json() == case['history']
    assert store_rows(path) == before


@pytest.mark.parametrize('case', [c for c in BASE['cases'] if c['activity_id'] in MERGED_OLD_IDS and c['stage'] == 'pending'], ids=lambda c: c['case'])
def test_retired_pending_offer_is_suppressed_without_replacement(tmp_path, case):
    path = tmp_path / 'fictitious-pending.sqlite'
    restore_store(path, case)
    coordinator = ChildOfferCoordinator(path)
    result = coordinator.evaluate('fictitious-fresh-evaluation', OfferEvidence(**case['operations'][0]['evidence']))
    assert result['reason'] == 'frozen_offer_no_longer_eligible'
    assert coordinator.history(case['profile_id']) == case['history']


@pytest.mark.parametrize('case', [c for c in BASE['cases'] if c['activity_id'] in MERGED_OLD_IDS and c['stage'] == 'delivered'], ids=lambda c: c['case'])
def test_response_to_delivered_predecessor_keeps_original_identity_and_text(tmp_path, case):
    path = tmp_path / 'fictitious-delivered.sqlite'
    restore_store(path, case)
    coordinator = ChildOfferCoordinator(path)
    original = case['history']['offers'][0]
    event = dict(profile_id=case['profile_id'], offer_id=original['offer_id'], event='selected',
                 occurred_at=original['created_at'], now=original['created_at'], selected_activity_id=case['activity_id'])
    recorded = coordinator.record_event('fictitious-new-old-selection', **event)
    assert recorded['offer']['selected_activity_id'] == case['activity_id']
    assert recorded['offer']['selection'] == original['selection']
    replay = ChildOfferCoordinator(path).record_event('fictitious-new-old-selection', **event)
    assert replay == {**recorded, 'replayed': True}
    assert len(coordinator.history(case['profile_id'])['events']) == 3


@pytest.mark.parametrize('merged_id,old_id', MERGE_CASES)
def test_new_parent_exclusion_also_suppresses_pending_merged_offer(tmp_path, merged_id, old_id):
    coordinator = ChildOfferCoordinator(tmp_path / 'fictitious-new-offer.sqlite', create=True)
    evidence = deepcopy(BASE['cases'][0]['operations'][0]['evidence'])
    evidence['eligibility'] = {'excluded_activity_ids': sorted(ACTIVITY_IDS - {merged_id})}
    generated = coordinator.evaluate('fictitious-merged-generation', OfferEvidence(**evidence))
    assert generated['offer']['activities_offered'] == [merged_id]
    evidence['eligibility']['excluded_activity_ids'].append(old_id)
    suppressed = coordinator.evaluate('fictitious-merged-now-excluded', OfferEvidence(**evidence))
    assert suppressed['reason'] == 'frozen_offer_no_longer_eligible'
    history = coordinator.history(evidence['profile_id'])
    assert len(history['offers']) == 1
    assert len(history['events']) == 1


def test_device_and_companion_filters_match_the_revised_variants():
    without_device = select_activities(request(eligibility={'allow_may_require_device_interaction': False}))
    assert not {'movement_dance_01', 'movement_sequence_01'} & {a['activity_id'] for a in without_device['activities']}
    for seed in range(12):
        without_company = recommend_activities('voluntary', eligibility=ActivityEligibility(allow_requires_other_person=False), n=30, random_seed=seed)
        assert all(not a.requires_other_person for a in without_company)
        assert 'social_conversation_story_01' not in {a.activity_id for a in without_company}
    daytime = {a.activity_id for a in recommend_activities('general', n=30, random_seed=0)}
    bedtime = {a.activity_id for a in recommend_activities('bedtime', n=30, random_seed=0)}
    assert 'creative_favorite_01' in daytime and 'creative_favorite_01' not in bedtime
    assert 'quiet_draw_01' not in daytime and 'quiet_draw_01' in bedtime


def test_unknown_stays_unknown_even_after_professional_content_review():
    with TestClient(create_app(Settings(token=TOKEN))) as client:
        answer = client.post('/v1/activities/eligibility', json={
            'request_id': 'fictitious-condition', 'considerations_state': 'known',
            'conditions': ['mobility_arms_hands']}, headers=HEADERS)
        assert answer.json()['eligibility_state'] == 'unknown'
        unavailable = client.post('/v1/activities/select', json=request(eligibility_state='unknown', eligibility=None), headers=HEADERS)
        assert unavailable.status_code == 400
        payload = request(eligibility_state='unknown')
        del payload['eligibility']
        unavailable = client.post('/v1/activities/select', json=payload, headers=HEADERS)
        assert unavailable.json()['reason'] == 'eligibility_unknown'
