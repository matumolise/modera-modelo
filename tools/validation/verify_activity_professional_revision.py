"""Comprueba el catálogo por HTTP interno y exporta las consignas para revisión humana."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from analytics_service.activities import CATALOG_VERSION, SELECTOR_VERSION
from analytics_service.http import create_app
from analytics_service.settings import Settings
from recommendations import (
    ACTIVITY_CATALOG, ACTIVITY_MERGE_PREDECESSORS, CHILD_ACTIVITY_INTRO_TEXT,
    FILTER_COMPATIBILITY_VERSION, RETIRED_ACTIVITY_IDS,
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description='Verificación ficticia y copia legible del catálogo revisado')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError('La carpeta de salida ya existe; usar otra para conservar la evidencia anterior.')
    token = 'fictitious-professional-catalog-check'
    headers = {'Authorization': 'Bearer ' + token}
    active_ids = {a.activity_id for a in ACTIVITY_CATALOG}
    require(len(active_ids) == 16, 'Cantidad de actividades distinta de la revisión entregada')
    require(not active_ids.intersection(RETIRED_ACTIVITY_IDS), 'Un ID retirado sigue activo')
    checked = []
    exclusions_checked = []
    with TestClient(create_app(Settings(token=token))) as client:
        health = client.get('/health').json()
        require(health['capabilities']['pmum']['state'] == 'DISABLED', 'PMUM debe seguir deshabilitado')
        for activity in ACTIVITY_CATALOG:
            payload = {'request_id': 'fictitious-review-' + activity.activity_id,
                       'context': activity.allowed_contexts[0], 'eligibility_state': 'known',
                       'eligibility': {'excluded_activity_ids': sorted(active_ids - {activity.activity_id})}}
            response = client.post('/v1/activities/select', json=payload, headers=headers)
            require(response.status_code == 200, 'Falló HTTP para ' + activity.activity_id)
            result = response.json()
            expected = json.loads(json.dumps(asdict(activity)))
            require(result['catalog_version'] == CATALOG_VERSION, 'Huella de catálogo inesperada')
            require(result['activities'] == [expected], 'La API no devolvió la consigna completa: ' + activity.activity_id)
            checked.append(expected)
        for merged_id, predecessors in ACTIVITY_MERGE_PREDECESSORS.items():
            for predecessor in sorted(predecessors):
                payload = {'request_id': 'fictitious-exclude-' + predecessor,
                           'context': 'voluntary', 'eligibility_state': 'known',
                           'eligibility': {'excluded_activity_ids': sorted((active_ids - {merged_id}) | {predecessor})}}
                response = client.post('/v1/activities/select', json=payload, headers=headers)
                require(response.status_code == 200 and response.json()['status'] == 'no_eligible_activities',
                        'Se perdió una exclusión explícita: ' + predecessor)
                exclusions_checked.append({'predecessor': predecessor, 'merged_activity': merged_id})
        for condition in ('mobility_arms_hands', 'visual', 'auditory', 'sensory'):
            response = client.post('/v1/activities/eligibility', json={
                'request_id': 'fictitious-condition-' + condition, 'considerations_state': 'known',
                'conditions': [condition]}, headers=headers)
            require(response.status_code == 200 and response.json()['eligibility_state'] == 'unknown',
                    'Una etiqueta se convirtió en compatibilidad automática')

    revision = json.loads((ROOT / 'docs/activity_catalog/REVISION_PROFESIONAL_2026-10-23.json').read_text(encoding='utf-8'))
    exported = {r['activity']['activity_id']: r['activity'] for r in revision['activities']}
    require(exported == {a['activity_id']: a for a in checked}, 'La revisión documentada no coincide con la API')
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    report = {'status': 'PASS', 'commit': commit, 'scope': 'controlled_fictitious_in_process_http_catalog_check',
              'catalog_version': CATALOG_VERSION, 'selector_version': SELECTOR_VERSION,
              'filter_compatibility_version': FILTER_COMPATIBILITY_VERSION,
              'activities_checked': len(checked), 'inherited_exclusions_checked': exclusions_checked,
              'professional_content_review': 'RECEIVED_WITH_DOCUMENTED_EDITS',
              'clinical_approval': False, 'child_effectiveness_validated': False,
              'docker_aws_android_validated': False, 'source_documents': revision['sources'],
              'runtime': {'python': sys.version.split()[0]}}
    lines = ['# Actividades de Moderá', '', CHILD_ACTIVITY_INTRO_TEXT, '']
    for index, activity in enumerate(checked, 1):
        lines += ['## ' + str(index) + '. ' + activity['title'], '',
                  'Identificador: `' + activity['activity_id'] + '`.', '',
                  'Contextos: ' + ', '.join(activity['allowed_contexts']) + '.', '',
                  activity['description'], '']
    output.mkdir(parents=True, exist_ok=False)
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'catalogo_para_revisar.md').write_text('\n'.join(lines), encoding='utf-8')
    print('PASS: 16 consignas completas por HTTP y cuatro exclusiones heredadas; evidencia ficticia. Sin validación Docker/AWS/Android.')


if __name__ == '__main__':
    main()
