"""Demo reproducible sin teléfono ni familias; conserva DTOs de tarjetas."""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from analytics_service.adult_messages import AdultMessageService


def payload(profile, values, evaluation, request):
    start=date(2026,1,5)
    return {"profile_id":profile,"series_id":profile+"-phone-assignment-v1","request_id":request,
            "evaluation_date":(start+timedelta(days=evaluation)).isoformat(),"time_zone":"America/Argentina/Buenos_Aires",
            "assignment_verified":True,"shared_phone":False,"context_declared":False,"c1_evidence_ids":[],
            "days":[{"date":(start+timedelta(days=i)).isoformat(),"revision":1,"minutes":v,"observed":True,"quality_verified":True} for i,v in enumerate(values)]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    with TemporaryDirectory() as directory:
        path=Path(directory)/"cards.sqlite3"
        service=AdultMessageService(path)
        increase=payload("demo-increase",[100]*14+[140]*14,28,"demo-1")
        decrease=payload("demo-decrease",[140]*14+[100]*14,28,"demo-2")
        outputs={"increase":service.evaluate(increase),"decrease":service.evaluate(decrease)}
        # Recarga real del repositorio; no se reconstruye el recibo del retry.
        service=AdultMessageService(path)
        outputs["replay_after_restart"]=service.evaluate(increase)
        outputs["return"]=service.evaluate(payload("demo-increase",[100]*14+[140]*14+[100]*14,42,"demo-3"))
        outputs["card_history"]=service.history("demo-increase")
        outputs["request_example"]=increase
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x") as file:
        json.dump(outputs,file,ensure_ascii=False,indent=2); file.write("\n")
    print("PASS: aumento, disminucion, replay tras reinicio, retorno e historial; datos ficticios")


if __name__=="__main__": main()
