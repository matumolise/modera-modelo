"""Actualización de catálogo con evidencia ficticia. Sin aprobación profesional."""

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from analytics_service.activities import (
    ACTIVITY_IDS, CATALOG_VERSION, SELECTOR_VERSION, InvalidSelection, select_activities,
)
from analytics_service.child_offers import ChildOfferCoordinator, OfferEvidence
from analytics_service.condition_mapping import resolve_considerations
from analytics_service.http import create_app
from analytics_service.settings import Settings
from recommendations import ACTIVITY_CATALOG, RETIRED_ACTIVITY_IDS, recommend_activities

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / 'tests/fixtures/catalog_revision/base_04f1e3a_fictitious.json'
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
BASE = FIXTURE['base_commit']
TOKEN = 'fictitious-catalog-upgrade-token'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}
EVALUATE = '/v1/child-offers/evaluate'
EVENTS = '/v1/child-offers/events'
NEW_IDS = {'social_create_together_01', 'quiet_story_ending_01',
           'creative_character_story_01', 'social_conversation_story_01'}
CURRENT_REVISION = ROOT / 'docs/activity_catalog/REVISION_PROFESIONAL_2026-10-23.json'
LATEST_FIXTURE = json.loads((ROOT / 'tests/fixtures/catalog_revision/base_1445056_fictitious.json').read_text(encoding='utf-8'))


def restore_fictitious_store(path, case):
    """Reconstruye el almacén serializado por el coordinador ORIGINAL, sin migrarlo."""
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
        db.execute('CREATE TABLE receipts (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, body TEXT NOT NULL)')
        db.execute('INSERT INTO state VALUES (1, ?)', (case['store']['state_body'],))
        db.executemany('INSERT INTO receipts VALUES (?, ?, ?)', case['store']['receipts'])


def stored_bytes(path):
    with sqlite3.connect(path) as db:
        return (db.execute('SELECT body FROM state WHERE id=1').fetchone()[0],
                db.execute('SELECT id, fingerprint, body FROM receipts ORDER BY id').fetchall())


def selection(**changes):
    return {'request_id': 'fictitious-catalog-selection', 'context': 'voluntary',
            'eligibility_state': 'known', 'eligibility': {}, **changes}


def test_current_source_correspondence_and_explicit_identity_changes():
    proposal = json.loads(CURRENT_REVISION.read_text(encoding='utf-8'))
    assert proposal['professional_status'] == 'SECOND_CONTENT_REVIEW_RECEIVED_AND_INCORPORATED_WITH_DOCUMENTED_EDITS'
    assert proposal['clinical_approval_claim'] is False
    assert len(ACTIVITY_CATALOG) == len(proposal['activities']) == 16
    previous_ids = {a['activity_id'] for a in FIXTURE['catalog']}
    assert ACTIVITY_IDS == (previous_ids - RETIRED_ACTIVITY_IDS) | NEW_IDS
    assert proposal['child_effectiveness_validated'] is False
    for activity, row in zip(ACTIVITY_CATALOG, proposal['activities']):
        assert json.loads(json.dumps(asdict(activity))) == row['activity']
        assert activity.description.startswith(('Necesitás:', 'No necesitás materiales.'))
    assert CATALOG_VERSION != FIXTURE['catalog_version']
    # El ranking publicado y sus pesos no cambian por editar el catálogo.
    assert SELECTOR_VERSION == FIXTURE['selector_version']


def test_reviewed_requirements_and_contexts_are_conservative():
    catalog = {a.activity_id: a for a in ACTIVITY_CATALOG}
    assert catalog['movement_dance_01'].may_require_device_interaction is True
    assert 'dejalo apoyado' in catalog['movement_dance_01'].description
    assert 'sentado o de pie' in catalog['movement_sequence_01'].description
    assert catalog['social_create_together_01'].requires_other_person is True
    assert catalog['quiet_story_ending_01'].requires_other_person is False
    assert catalog['quiet_story_ending_01'].activity_level == 'calm'
    assert {'writing', 'drawing', 'stories'} <= set(catalog['creative_character_story_01'].interest_tags)
    assert 'bedtime' not in catalog['creative_favorite_01'].allowed_contexts
    assert catalog['social_conversation_story_01'].requires_other_person is True
    for context in ('general', 'voluntary', 'bedtime'):
        for seed in range(12):
            chosen = recommend_activities(context, n=30, random_seed=seed)
            assert not RETIRED_ACTIVITY_IDS & {a.activity_id for a in chosen}
            if context == 'bedtime':
                assert all(a.bedtime_suitable and a.activity_level == 'calm' for a in chosen)


def test_old_identifiers_and_interests_are_accepted_without_aliasing():
    old_interests = sorted({tag for a in FIXTURE['catalog'] for tag in a['interest_tags']})
    result = select_activities(selection(interests=old_interests,
        recently_shown_ids=sorted(RETIRED_ACTIVITY_IDS),
        eligibility={'excluded_activity_ids': sorted(ACTIVITY_IDS | RETIRED_ACTIVITY_IDS)}))
    assert result['status'] == 'no_eligible_activities'
    baseline = recommend_activities('general', random_seed=8)
    assert recommend_activities('general', random_seed=8,
        selected_activity_counts={aid: 10000 for aid in RETIRED_ACTIVITY_IDS}) == baseline
    for field in ('recently_shown_ids',):
        with pytest.raises(InvalidSelection):
            select_activities(selection(**{field: ['not-an-activity']}))
    with pytest.raises(InvalidSelection):
        select_activities(selection(eligibility={'excluded_activity_ids': ['not-an-activity']}))


def test_conditions_are_not_reinterpreted_as_medically_approved_filters():
    assert resolve_considerations({'request_id': 'fictitious-none',
        'considerations_state': 'known', 'conditions': ['none']})['eligibility_state'] == 'known'
    for condition in ('mobility_arms_hands', 'mobility_legs', 'mobility_both', 'visual', 'auditory', 'sensory'):
        result = resolve_considerations({'request_id': 'fictitious-condition',
            'considerations_state': 'known', 'conditions': [condition]})
        assert result['eligibility_state'] == 'unknown'
        assert result['reason'] == 'functional_mapping_required'
        assert 'eligibility' not in result
    result = select_activities({'request_id': 'fictitious-unknown', 'context': 'voluntary',
        'eligibility_state': 'unknown'})
    assert result['reason'] == 'eligibility_unknown'
    assert result['activities'] == []


@pytest.mark.parametrize('activity_id', sorted(RETIRED_ACTIVITY_IDS))
def test_legacy_responses_preserve_retired_ids_without_new_offers(tmp_path, activity_id):
    from datetime import datetime, timezone
    from intervention_history import (
        InterventionOffer, append_intervention_offer, append_intervention_record,
        create_intervention_offer, create_intervention_record,
    )
    from intervention_history_reader import read_linked_offer_responses

    path = tmp_path / 'fictitious-legacy.jsonl'
    when = datetime(2026, 10, 16, 13, tzinfo=timezone.utc)
    original = InterventionOffer('fictitious-legacy-offer', 1, when.isoformat(),
                                 'child_initiated', 'voluntary', (activity_id,))
    append_intervention_offer(original, str(path))
    prefix = path.read_bytes()
    record = create_intervention_record(1, 'child_initiated', 'voluntary',
        (activity_id,), 'selected', activity_id, when, original.offer_id)
    append_intervention_record(record, str(path))
    after = path.read_bytes()
    assert after.startswith(prefix)
    append_intervention_record(record, str(path))
    assert path.read_bytes() == after
    assert record.selected_activity_id == activity_id
    assert len(read_linked_offer_responses(path)) == 1
    with pytest.raises(ValueError):
        create_intervention_offer(1, 'child_initiated', 'voluntary', (activity_id,), when)
    with pytest.raises(ValueError):
        create_intervention_record(1, 'child_initiated', 'voluntary',
            ('not-an-activity',), 'selected', 'not-an-activity', when)


@pytest.mark.parametrize('case', FIXTURE['cases'], ids=lambda c: c['case'])
def test_original_receipts_survive_catalog_upgrade_and_http_restart(tmp_path, case):
    path = tmp_path / 'fictitious-upgrade.sqlite'
    restore_fictitious_store(path, case)
    before = stored_bytes(path)
    settings = Settings(token=TOKEN, child_offers_enabled=True, child_offers_repository_path=path)
    for _ in range(2):
        with TestClient(create_app(settings)) as client:
            assert client.get('/health').status_code == 200
            for op in case['operations']:
                if op['kind'] == 'evaluate':
                    response = client.post(EVALUATE, json={'request_id': op['request_id'], 'evidence': op['evidence']}, headers=HEADERS)
                else:
                    response = client.post(EVENTS, json={'request_id': op['request_id'], **op['payload']}, headers=HEADERS)
                assert response.status_code == 200
                assert response.json() == {**op['receipt'], 'replayed': True}
                assert response.json()['offer']['selection']['catalog_version'] == FIXTURE['catalog_version']
            history = client.get('/v1/child-offers/profiles/' + case['profile_id'] + '/history', headers=HEADERS)
            assert history.json() == case['history']
    assert stored_bytes(path) == before


@pytest.mark.parametrize('case', FIXTURE['cases'][:2], ids=lambda c: c['case'])
def test_pending_retired_offer_is_not_replaced_or_presented_again(tmp_path, case):
    path = tmp_path / 'fictitious-pending.sqlite'
    restore_fictitious_store(path, case)
    c = ChildOfferCoordinator(path)
    op = case['operations'][0]
    evidence = OfferEvidence(**{**op['evidence'], 'interests': tuple(op['evidence']['interests'])})
    result = c.evaluate('fictitious-fresh-after-upgrade', evidence)
    assert result['reason'] == 'frozen_offer_no_longer_eligible'
    history = c.history(case['profile_id'])
    assert history['offers'] == case['history']['offers']
    assert history['events'] == case['history']['events']
    assert len(history['offers']) == 1


def test_selection_of_already_delivered_retired_activity_preserves_original_snapshot(tmp_path):
    case = FIXTURE['cases'][1]
    path = tmp_path / 'fictitious-delivered.sqlite'
    restore_fictitious_store(path, case)
    c = ChildOfferCoordinator(path)
    original = case['history']['offers'][0]
    kwargs = dict(profile_id=case['profile_id'], offer_id=original['offer_id'], event='selected',
        occurred_at='2026-10-16T10:01:00-03:00', now='2026-10-16T10:01:00-03:00',
        selected_activity_id=case['activity_id'])
    recorded = c.record_event('fictitious-old-offer-response', **kwargs)
    assert recorded['offer']['selection'] == original['selection']
    assert recorded['offer']['selected_activity_id'] == 'quiet_prepare_01'
    assert ChildOfferCoordinator(path).record_event('fictitious-old-offer-response', **kwargs) == {**recorded, 'replayed': True}
    assert len(c.history(case['profile_id'])['events']) == len(case['history']['events']) + 1
    # Una oferta nueva también debe aceptar el ID retirado en la historia reciente.
    evidence = deepcopy(case['operations'][0]['evidence'])
    evidence.update(interval_id='fictitious-after-retired-selection',
        interval_started_at='2026-10-16T12:00:00-03:00', now='2026-10-16T13:00:00-03:00', eligibility={})
    fresh = c.evaluate('fictitious-after-retired-selection',
        OfferEvidence(**{**evidence, 'interests': tuple(evidence['interests'])}))
    assert fresh['status'] == 'offer'
    assert not RETIRED_ACTIVITY_IDS & set(fresh['offer']['activities_offered'])
    assert c.history(case['profile_id'])['offers'][0]['selection'] == original['selection']


def test_pending_activity_with_same_identity_keeps_its_original_text(tmp_path):
    case = next(c for c in LATEST_FIXTURE['cases'] if c['case'] == 'creative_favorite_01-pending')
    path = tmp_path / 'fictitious-original-pending.sqlite'
    restore_fictitious_store(path, case)
    evidence = deepcopy(case['operations'][0]['evidence'])
    c = ChildOfferCoordinator(path)
    result = c.evaluate('fictitious-same-pending-new-request',
        OfferEvidence(**{**evidence, 'interests': tuple(evidence['interests'])}))
    assert result['offer'] == case['history']['offers'][0]
    assert result['offer']['selection']['catalog_version'] == LATEST_FIXTURE['catalog_version']
    assert len(c.history(case['profile_id'])['offers']) == 1


def test_new_offer_after_old_history_uses_current_catalog_and_original_history_survives(tmp_path):
    case = FIXTURE['cases'][2]
    path = tmp_path / 'fictitious-new.sqlite'
    restore_fictitious_store(path, case)
    c = ChildOfferCoordinator(path)
    e = deepcopy(case['operations'][0]['evidence'])
    e.update(interval_id='fictitious-new-interval', interval_started_at='2026-10-16T12:00:00-03:00',
        now='2026-10-16T13:00:00-03:00', eligibility={})
    result = c.evaluate('fictitious-current-evaluation', OfferEvidence(**{**e, 'interests': tuple(e['interests'])}))
    assert result['status'] == 'offer'
    assert result['offer']['selection']['catalog_version'] == CATALOG_VERSION
    assert len(c.history(case['profile_id'])['offers']) == 2
    assert c.history(case['profile_id'])['offers'][0] == case['history']['offers'][0]
    assert result['offer']['offer_id'] != case['history']['offers'][0]['offer_id']


def test_http_returns_full_revised_text_without_changing_activity_schema(tmp_path):
    expected_fields = set(FIXTURE['catalog'][0])
    with TestClient(create_app(Settings(token=TOKEN))) as client:
        for activity in ACTIVITY_CATALOG:
            payload = selection(eligibility={'excluded_activity_ids': sorted(ACTIVITY_IDS - {activity.activity_id})},
                context=activity.allowed_contexts[0])
            response = client.post('/v1/activities/select', json=payload, headers=HEADERS)
            assert response.status_code == 200
            shown = response.json()['activities']
            assert len(shown) == 1
            assert set(shown[0]) == expected_fields
            assert shown[0]['description'] == activity.description
            assert shown[0]['title'] == activity.title
        health = client.get('/health').json()['capabilities']
        assert health['activities']['catalog_status'] == 'PROVISIONAL'
        assert health['pmum']['state'] == 'DISABLED'
