"""Perfil fijo sobre entradas ficticias existentes; no optimiza parámetros."""
import argparse
from collections import Counter
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from analytics_service.adult_messages import advance, CONFIG, CONFIG_FINGERPRINT


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--inputs",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    source=json.loads(args.inputs.read_text(encoding="utf-8"))
    series=source["series"].copy()
    for original in source["series"]:
        if original["scenario"]!="S0": continue
        values=original["values"]
        for name in ("LOW25","LOW50","RETURN14","ONE_LOW_DAY"):
            changed=[]
            for i,value in enumerate(values):
                multiplier = (0.75 if name=="LOW25" else 0.5) if name in ("LOW25","LOW50") and i>=56 else 1
                if name=="RETURN14" and 56<=i<70: multiplier=1.5
                if name=="ONE_LOW_DAY" and i>=56: multiplier=1.5
                changed.append(0 if name=="ONE_LOW_DAY" and i==84 else round(value*multiplier))
            series.append({**original,"scenario":name,"input_id":original["input_id"].replace("S0",name),"values":changed})
    decisions=[]; summaries={}
    start=date(2026,1,5)
    for index,s in enumerate(series):
        state=None; created=[]; counts=Counter()
        for day in range(28,113,7):
            p={"profile_id":s["input_id"],"series_id":s["input_id"],"evaluation_date":(start+timedelta(days=day)).isoformat(),
               "time_zone":"America/Argentina/Buenos_Aires","assignment_verified":True,"shared_phone":False,"context_declared":False,
               "c1_evidence_ids":[],"days":[{"date":(start+timedelta(days=i)).isoformat(),"revision":1,"minutes":v,"observed":True,"quality_verified":True} for i,v in enumerate(s["values"][:day])]}
            state,r=advance(state,p)
            if r["action"]=="CREATE": created.append((day,r["card"]["direction"]))
            counts[r["status"]]+=1
            decisions.append({"input_id":s["input_id"],"day":day,"status":r["status"],"action":r["action"],"card_id":r["card"]["card_id"] if r["card"] else None})
        key=(s["scenario"],s["sigma"])
        cell=summaries.setdefault(key,{"scenario":key[0],"sigma":key[1],"n":0,"series_with_card_report":0,"cards_report":0,"increase_report":0,"decrease_report":0,"preexisting_card_at_56":0,"statuses":Counter(),"expected_direction_delays":[],"without_expected_direction":0})
        cell["n"]+=1
        report=[c for c in created if 56<c[0]<=112]
        cell["cards_report"]+=len(report); cell["series_with_card_report"]+=bool(report)
        cell["increase_report"]+=sum(d=="INCREASE" for _,d in report)
        cell["decrease_report"]+=sum(d=="DECREASE" for _,d in report)
        # Aperturas previas, no necesariamente episodios vigentes.
        cell["preexisting_card_at_56"]+=any(day<=56 for day,_ in created)
        cell["statuses"].update(counts)
        expected="DECREASE" if s["scenario"] in {"LOW25","LOW50"} else "INCREASE" if s["scenario"] in {"S2a","S2b","RETURN14","ONE_LOW_DAY"} else None
        if expected:
            found=[day-56 for day,d in created if day>56 and d==expected]
            if found: cell["expected_direction_delays"].append(min(found))
            else: cell["without_expected_direction"]+=1
        if (index+1)%100==0: print(f"Procesadas {index+1}/{len(series)} series",flush=True)
    result={"source_sha256":hashlib.sha256(args.inputs.read_bytes()).hexdigest(),"configuration":CONFIG,"configuration_fingerprint":CONFIG_FINGERPRINT,
            "scope":"dependent_fictitious_series_internal_profile_evaluation", "n_series":len(series),"n_evaluations":len(decisions),"cells":list(summaries.values()),"decisions":decisions}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"n_series":len(series),"n_evaluations":len(decisions),"output":str(args.output)}))


if __name__=="__main__": main()
