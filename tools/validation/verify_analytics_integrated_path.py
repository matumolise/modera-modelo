"""Ensayo ficticio en proceso: bytes F12 -> preparador -> C1 -> tarjetas.

Reutiliza productor de fixtures, adaptadores y API existentes. No valida Android,
backend real, cobertura física, perfiles de producto ni eficacia con familias.
"""
import argparse
from contextlib import closing, ExitStack
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sqlite3
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from analytics_service.f12_export import prepare_android_export
from analytics_service.http import create_app
from analytics_service.settings import Settings
from tests.test_f12_export_integration import synthetic_export, encode
from tools.integration.verify_f12_phone_parity import load_packet

TOKEN = "integrated-fictitious-test-token"
HEADERS = {"Authorization": "Bearer " + TOKEN}
START = date(2026, 1, 5)  # Lunes, antes de todos los días evaluados.
SCOPE = "FICTITIOUS_IN_PROCESS_ANALYTICS_PATH"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def post(client, route, payload):
    response = client.post(route, headers=HEADERS, json=payload)
    require(response.status_code == 200, f"{route}: {response.status_code}: {response.text}")
    return response.json()


def get(client, route):
    response = client.get(route, headers=HEADERS)
    require(response.status_code == 200, f"{route}: {response.status_code}: {response.text}")
    return response.json()


def message_snapshot(path):
    # Comparación lógica de TODOS los registros, sin depender de bytes SQLite.
    with closing(sqlite3.connect(path.as_uri()+"?mode=ro", uri=True)) as db:
        return {table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in ("config", "states", "receipts", "evaluations", "revisions", "cards")}


def controlled_export(case, index, planned_minutes):
    day = START + timedelta(days=index)
    binding, summary, events = synthetic_export(day.isoformat(), planned_minutes or 0)
    binding["series"].update(profile_id="fixture-profile-"+case,
                             device_id="fixture-device-"+case,
                             assignment_id="fixture-assignment-"+case)
    binding["request_id"] = f"fixture-historical-{case}-{day.isoformat()}"
    run_id = str(UUID(bytes=sha256(f"FICTITIOUS:{case}:{day}".encode()).digest()[:16], version=4))
    summary["collectorRunId"] = run_id
    for event in events:
        event["collectorRunId"] = run_id
    if planned_minutes is None:
        summary.update(eventCount=0, usageAccessAvailable=False,
                       errorCode="USAGE_ACCESS_NOT_GRANTED",
                       errorMessage="FICTITIOUS permission failure")
        events = []
    # Oráculo del ensayo: zona Buenos Aires, jornada UTC03:00->UTC03:00;
    # consulta completa, estado OFF conocido antes del día y dos transiciones
    # exactas. No se deriva calidad de coverage ni del éxito del preparador.
    begin = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)+timedelta(hours=3)
    end = begin+timedelta(days=1)
    begin_ms, end_ms = int(begin.timestamp()*1000), int(end.timestamp()*1000)
    require(summary["requestedBeginEpochMs"] == begin_ms-3600000 and
            summary["requestedEndEpochMs"] == end_ms, "fixture query bounds")
    if planned_minutes is not None:
        require(summary["errorCode"] is None and summary["usageAccessAvailable"], "fixture permission")
        require(summary["eventCount"] == len(events), "fixture declared event count")
        require(len(events) == (3 if planned_minutes else 1), "fixture event completeness")
        require(events[0]["eventTypeName"] == "SCREEN_NON_INTERACTIVE" and
                events[0]["eventTimeEpochMs"] == begin_ms-1800000, "fixture initial state")
        if planned_minutes:
            require(events[1]["eventTypeName"] == "SCREEN_INTERACTIVE" and
                    events[2]["eventTypeName"] == "SCREEN_NON_INTERACTIVE", "fixture transitions")
            require(events[1]["eventTimeEpochMs"] == begin_ms+10*3600000 and
                    events[2]["eventTimeEpochMs"]-events[1]["eventTimeEpochMs"] == planned_minutes*60000,
                    "fixture planned duration")
    return binding, encode(summary, events), begin.isoformat(), end.isoformat()


def run_case(root, name, baseline, changed, length, *, missing_index=None, withheld_index=None):
    root.mkdir()
    raw_root=root/"raw"; raw_root.mkdir()
    settings=Settings(token=TOKEN, activities_enabled=False, historical_enabled=True,
                      historical_config_path=ROOT/"tests/fixtures/historical_c1_smoke_only.json",
                      historical_repository_path=root/"history.json",
                      adult_messages_enabled=True, adult_messages_repository_path=root/"messages.sqlite3")
    planned=[baseline+(0,2,-2,4,-4,1,-1)[i%7] if i<14 or i>=28
             else changed+(0,2,-2,4,-4,1,-1)[i%7] for i in range(length)]
    if missing_index is not None: planned[missing_index]=None
    message_days=[]; daily=[]; messages=[]; last_send=0; series_id=None
    continuity_restarts=0
    with ExitStack() as lifetimes:
        client=lifetimes.enter_context(TestClient(create_app(settings)))
        health=get(client,"/health")
        require(health["capabilities"]["historical"]["configuration_id"] == "smoke-only-not-calibrated", "smoke profile required")
        require(health["capabilities"]["pmum"]["state"] == "DISABLED", "PMUM must not participate")
        for index, minutes in enumerate(planned):
            if index in (28,35):
                saved_c1=settings.historical_repository_path.read_bytes()
                saved_messages=message_snapshot(settings.adult_messages_repository_path)
                lifetimes.close()
                client=lifetimes.enter_context(TestClient(create_app(settings)))
                old_c1=post(client,"/v1/historical/evaluate",daily[-1]["historical_request"])
                require(old_c1["replayed"] and old_c1["result"] == daily[-1]["historical_receipt"]["result"],
                        "continuity restart changed historical receipt")
                old_message=post(client,"/v1/adult-messages/evaluate",messages[-1]["request"])
                require(old_message == {**messages[-1]["response"],"replayed":True},
                        "continuity restart changed message receipt")
                require(settings.historical_repository_path.read_bytes() == saved_c1 and
                        message_snapshot(settings.adult_messages_repository_path) == saved_messages,
                        "continuity retry advanced persisted state")
                continuity_restarts+=1
            binding, pair, begin, end=controlled_export(name,index,minutes)
            directory=raw_root/binding["local_date"]; directory.mkdir()
            write_json(directory/"binding.json",binding)
            (directory/"summary.json").write_bytes(pair[0])
            (directory/"events.jsonl").write_bytes(pair[1])
            prepared=prepare_android_export(binding,[pair])
            # Un día de cada serie pasa además por el CLI offline publicado,
            # conservando bytes/manifest y cargando su request real de archivo.
            if index == 0:
                completed=subprocess.run([sys.executable,str(ROOT/"tools/integration/build_historical_request_from_export.py"),
                    "--binding",str(directory/"binding.json"),"--run",str(directory/"summary.json"),str(directory/"events.jsonl"),
                    "--output-dir",str(root/"first_packet")],capture_output=True)
                require(completed.returncode == 0, "preparer CLI failed: "+completed.stderr.decode("utf-8",errors="replace"))
                _,_,archived=load_packet(root/"first_packet")
                require(archived == prepared["request"], "CLI and adapter diverged")
                request=archived
            else:
                request=prepared["request"]
            rep=request["representation"]
            expected_status="MISSING" if minutes is None else "OBSERVED_ZERO" if minutes == 0 else "OBSERVED"
            require(rep["status"] == expected_status and rep["value"] == minutes, "representation vs oracle")
            require(rep["interval_start"] == begin and rep["interval_end"] == end, "interval trace")
            require(rep["coverage"]["value"] is None, "coverage was invented")
            require(not prepared["audit"]["physical_capture_verified"] and
                    not prepared["audit"]["device_identity_verified"] and
                    not prepared["audit"]["coverage_quantified"], "physical approval was invented")
            original=prepared["audit"]["originals"][0]
            require(original["summary_sha256"] == sha256(pair[0]).hexdigest() and
                    original["events_sha256"] == sha256(pair[1]).hexdigest(), "raw lineage hashes")
            require(original["collector_run_id"] == json.loads(pair[0])["collectorRunId"], "collector identity")
            series_id=series_id or rep["subject_id"]
            require(rep["subject_id"] == series_id, "series split unexpectedly")
            receipt=post(client,"/v1/historical/evaluate",request)
            require(not receipt["replayed"], "first historical call was replay")
            evaluation=receipt["result"]["evaluation"]
            require(evaluation["subject_id"] == series_id and
                    evaluation["representation_record_id"] == rep["representation_record_id"] and
                    evaluation["observed_value"] == minutes and
                    evaluation["evaluated_interval_start"] == begin and
                    evaluation["evaluated_interval_end"] == end, "C1 trace mismatch")
            if minutes is None:
                require(evaluation["outcome"] == "ABSTAIN", "missing C1 did not abstain")
                if daily:
                    require(receipt["result"]["next_state"] == daily[-1]["historical_receipt"]["result"]["next_state"], "missing advanced C1")
            quality=minutes is not None and index != withheld_index
            row={"date":binding["local_date"],"revision":1,"minutes":rep["value"],
                 "observed":minutes is not None,"quality_verified":quality}
            message_days.append(row)
            entry={"scope":SCOPE,"local_date":binding["local_date"],"binding":binding,
                   "lineage":prepared["audit"],"historical_request":request,"historical_receipt":receipt,
                   "message_day":row,"fixture_attestation":{"controlled_fixture":True,
                       "quality_verified_for_fixture":quality,"physical_capture_verified":False,
                       "basis":"WITHHELD_FOR_TEST" if index == withheld_index else "MISSING_PERMISSION_FIXTURE" if minutes is None else "EXACT_PLANNED_EVENTS_AND_CLOSED_QUERY"}}
            daily.append(entry)
            count=index+1
            if count >= 28 and count%7 == 0:
                msg={"request_id":f"fixture-message-{name}-{count}","profile_id":binding["series"]["profile_id"],
                     "series_id":series_id,"time_zone":binding["series"]["time_zone"],
                     "evaluation_date":(START+timedelta(days=count)).isoformat(),
                     "assignment_verified":True,"shared_phone":False,"context_declared":False,
                     "days":deepcopy(message_days[last_send:]),
                     "c1_evidence_ids":[e["historical_receipt"]["result"]["evaluation"]["evaluation_id"] for e in daily]}
                result=post(client,"/v1/adult-messages/evaluate",msg)
                require(not result["replayed"], "first message call was replay")
                require(result["c1_evidence_ids"] == sorted(msg["c1_evidence_ids"]), "C1 evidence link missing")
                if result["card"]:
                    card=result["card"]
                    require(card["series_id"] == series_id and card["profile_id"] == msg["profile_id"] and
                            card["evaluation_date"] == msg["evaluation_date"] and
                            card["time_zone"] == msg["time_zone"] and card["recommendation"], "card trace mismatch")
                    require(card["delivery_status"] == "CANDIDATE_NOT_DELIVERED", "rendering falsely claimed")
                messages.append({"request":msg,"response":result}); last_send=count
        profile="fixture-profile-"+name
        history=get(client,f"/v1/adult-messages/profiles/{profile}/history")
        expected_versions=[{"version":e["response"]["card_version"],"card":e["response"]["card"]}
                           for e in messages if e["response"]["card"]]
        require(history["versions"] == expected_versions, "history lost original DTO versions")
    historical_bytes=settings.historical_repository_path.read_bytes()
    before_messages=message_snapshot(settings.adult_messages_repository_path)
    # Nueva aplicación/runtimes sobre los mismos stores, no un retry en caché.
    with TestClient(create_app(settings)) as restarted:
        for entry in daily:
            replay=post(restarted,"/v1/historical/evaluate",entry["historical_request"])
            require(replay["replayed"] and replay["result"] == entry["historical_receipt"]["result"], "historical replay changed original")
        for entry in messages:
            replay=post(restarted,"/v1/adult-messages/evaluate",entry["request"])
            expected={**entry["response"],"replayed":True}
            require(replay == expected, "message replay changed original")
        require(get(restarted,f"/v1/adult-messages/profiles/{profile}/history") == history,
                "replay duplicated or altered cards")
    require(settings.historical_repository_path.read_bytes() == historical_bytes, "historical replay rewrote store")
    require(message_snapshot(settings.adult_messages_repository_path) == before_messages,
            "message replay changed state, receipts, revisions or versions")
    result={"scope":SCOPE,"case":name,"series_id":series_id,"n_days":length,
            "daily_trace":daily,"message_evaluations":messages,"card_history":history,
            "coverage_remains_unknown":True,"physical_capture_verified":False,
            "quality_basis":"CONTROLLED_FIXTURE_ORACLE_ONLY",
            "restart_kind":"APPLICATION_AND_RUNTIME_RECREATED_SAME_STORES",
            "continuity_restarts_before_new_days":continuity_restarts,
            "historical_replay_original":True,"historical_store_bytes_unchanged":True,
            "message_replay_original":True,"card_history_unchanged_after_replay":True}
    result["message_store_records_unchanged"] = True
    write_json(root/"result.json",result)
    return result


def run(output):
    output=Path(output).resolve(); output.mkdir(parents=False,exist_ok=False)
    cases=[run_case(output/"increase_return","increase_return",100,140,42),
           run_case(output/"decrease_return","decrease_return",140,100,42),
           run_case(output/"missing_day","missing_day",100,140,28,missing_index=10),
           run_case(output/"quality_withheld","quality_withheld",100,140,28,withheld_index=20)]
    for case in cases[:2]:
        results=[entry["response"] for entry in case["message_evaluations"]]
        require([r["status"] for r in results] == ["ACTIVE","INCONCLUSIVE","RESOLVED"], "episode transition mismatch")
        expected="INCREASE" if case["case"] == "increase_return" else "DECREASE"
        require(results[0]["card"]["direction"] == expected and
                len({r["card"]["card_id"] for r in results}) == 1 and
                [r["card_version"] for r in results] == [1,2,3], "episode or version mismatch")
        require(results[0]["card"]["statistics"]["delta"] == (40 if expected == "INCREASE" else -40), "opening magnitude mismatch")
        require(results[-1]["card"]["statistics"]["delta"] == 0, "return magnitude mismatch")
        base=100 if expected == "INCREASE" else 140
        for step, result in enumerate(results):
            card=result["card"]
            require(card["opening_reference_start"] == START.isoformat() and
                    card["opening_recent_start"] == (START+timedelta(days=14)).isoformat() and
                    card["comparison_recent_start"] == (START+timedelta(days=14+7*step)).isoformat(),
                    "frozen reference or recent dates changed")
            require(card["statistics"]["reference"] == base and
                    card["statistics"]["delta"] == ((40 if expected == "INCREASE" else -40)*(2-step)/2),
                    "frozen reference or update magnitude mismatch")
    for case in cases[2:]:
        result=case["message_evaluations"][0]["response"]
        require(result["status"] == "INSUFFICIENT_DATA" and result["card"] is None and
                case["card_history"]["versions"] == [], "insufficient evidence produced card")
    require(len({c["series_id"] for c in cases}) == len(cases), "fixture series collision")
    identifiers=[e["historical_request"]["representation"]["representation_record_id"]
                 for c in cases for e in c["daily_trace"]]
    require(len(set(identifiers)) == 140, "fixture record collision")
    report={"scope":SCOPE,"result":"PASS","n_cases":4,"historical_first_evaluations":140,
            "message_first_evaluations":8,"restart_replay_historical_requests":140,
            "restart_replay_message_requests":8,"physical_capture_verified":False,
            "continuity_restarts_before_new_days":sum(c["continuity_restarts_before_new_days"] for c in cases),
            "additional_continuity_retries":{"historical":4,"messages":4},
            "real_backend_verified":False,"socket_or_process_restart_verified":False,
            "orchestration":"TEST_HARNESS_CALLS_EXISTING_ENDPOINTS; NOT_AUTOMATIC_PRODUCTION_WIRING",
            "c1_configuration_id":"smoke-only-not-calibrated",
            "summary":[{"case":c["case"],"series_id":c["series_id"],"n_days":c["n_days"],
                        "statuses":[e["response"]["status"] for e in c["message_evaluations"]],
                        "card_versions":len(c["card_history"]["versions"])} for c in cases]}
    write_json(output/"REPORT.json",report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.output_dir)
    print("PASS: 4 fictitious integrated cases; runtime restart/replay verified. No physical/backend validation.")


if __name__ == "__main__": main()
