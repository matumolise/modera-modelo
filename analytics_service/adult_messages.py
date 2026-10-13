"""Política de tarjetas adultas del candidato interno; independiente de C1/PMUM.

Persistencia transaccional de evaluación, episodio y versiones. No entrega push,
no acredita visualización y no habilita por sí sola uso con familias.
"""
from datetime import date, datetime, timedelta, timezone
from contextlib import closing
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = "adult-messages-internal-candidate-v1"
CONFIG = {
    "version": VERSION, "window_days": 14, "increase_minutes": 20,
    "minimum_direction_days": 10, "return_margin_minutes": 5,
    "maximum_episode_days": 56, "cooldown_days": 14,
    "maximum_new_cards": 1, "limit_period_days": 28,
    "c1_role": "complementary_technical_evidence", "pmum_role": "none",
    "scope": "internal_candidate_not_family_validated",
}


class MessageConflict(ValueError):
    pass


class MessageUnavailable(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


CONFIG_FINGERPRINT = digest(CONFIG)


def parse_day(value):
    if not isinstance(value, str):
        raise ValueError("invalid_date")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("invalid_date")
    return parsed


def identifier(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 128 or value.strip() != value:
        raise ValueError("invalid_identifier")
    return value


def parse_payload(payload):
    required = {"request_id", "profile_id", "series_id", "time_zone", "evaluation_date",
                "assignment_verified", "shared_phone", "context_declared", "days", "c1_evidence_ids"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("invalid_message_fields")
    p = dict(payload)
    for name in ("request_id", "profile_id", "series_id", "time_zone"):
        identifier(p[name])
    try:
        ZoneInfo(p["time_zone"])
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("invalid_time_zone") from None
    evaluation = parse_day(p["evaluation_date"])
    if evaluation.weekday() != 0:
        raise ValueError("evaluation_requires_monday")
    if evaluation > datetime.now(ZoneInfo(p["time_zone"])).date():
        raise ValueError("future_evaluation")
    for flag in ("assignment_verified", "shared_phone", "context_declared"):
        if type(p[flag]) is not bool:
            raise ValueError("explicit_context_required")
    if not isinstance(p["days"], list) or len(p["days"]) > 366:
        raise ValueError("invalid_days")
    seen = set()
    for row in p["days"]:
        if not isinstance(row, dict) or set(row) != {"date", "revision", "minutes", "observed", "quality_verified"}:
            raise ValueError("invalid_daily_record")
        day = parse_day(row["date"])
        if day >= evaluation or day in seen:
            raise ValueError("future_or_duplicate_day")
        seen.add(day)
        if type(row["revision"]) is not int or row["revision"] < 1:
            raise ValueError("invalid_revision")
        if type(row["observed"]) is not bool or type(row["quality_verified"]) is not bool:
            raise ValueError("invalid_daily_quality")
        minutes = row["minutes"]
        if row["observed"]:
            # Decimal de JSON: sin coerción de strings, bool, NaN o Infinity.
            tz = ZoneInfo(p["time_zone"])
            start = datetime.combine(day, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
            end = datetime.combine(day+timedelta(days=1), datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
            if type(minutes) not in (int, float) or not 0 <= minutes <= (end-start).total_seconds()/60:
                raise ValueError("invalid_minutes")
        elif minutes is not None:
            raise ValueError("missing_is_not_zero")
    ids = p["c1_evidence_ids"]
    if not isinstance(ids, list) or len(ids) > 366:
        raise ValueError("invalid_c1_evidence")
    for value in ids:
        identifier(value)
    p["c1_evidence_ids"] = sorted(set(ids))
    p["days"] = sorted([dict(row) for row in p["days"]], key=lambda row: row["date"])
    return p


def usable(rows):
    return len(rows) == 14 and all(row and row["observed"] and row["quality_verified"] for row in rows)


def window(days, start):
    return [days.get((start+timedelta(days=i)).isoformat()) for i in range(14)]


def level(rows):
    total = Fraction(0)
    for weekend, weight in ((False, Fraction(5,7)), (True, Fraction(2,7))):
        values = [Fraction(str(row["minutes"])) for row in rows
                  if row and (parse_day(row["date"]).weekday() >= 5) == weekend]
        total += weight*sum(values)/len(values)
    return total


def statistics(recent, reference):
    if not usable(recent) or not usable(reference):
        return None
    delta = level(recent)-level(reference)
    excluded = []
    for side, rows in enumerate((recent, reference)):
        for i in range(14):
            copy = rows.copy(); copy[i] = None
            excluded.append(level(copy)-level(reference) if side == 0 else level(recent)-level(copy))
    means = {}
    for weekend in (False, True):
        values = [Fraction(str(r["minutes"])) for r in reference
                  if (parse_day(r["date"]).weekday() >= 5) == weekend]
        means[weekend] = sum(values)/len(values)
    above = below = 0
    for row in recent:
        value = Fraction(str(row["minutes"]))
        baseline = means[parse_day(row["date"]).weekday() >= 5]
        above += value > baseline; below += value < baseline
    return {"recent": level(recent), "reference": level(reference), "delta": delta,
            "minimum": min(excluded), "maximum": max(excluded), "above": above, "below": below}


def direction(stats):
    if stats is None:
        return None
    m, k = CONFIG["increase_minutes"], CONFIG["minimum_direction_days"]
    if stats["delta"] >= m and stats["minimum"] >= m and stats["above"] >= k:
        return "INCREASE"
    if stats["delta"] <= -m and stats["maximum"] <= -m and stats["below"] >= k:
        return "DECREASE"
    return None


def rounded(value):
    return int((Decimal(value.numerator)/Decimal(value.denominator)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def duration(value):
    total = rounded(value)
    return f"{total//60} h {total%60:02d} min" if total >= 60 else f"{total} min"


def make_card(episode, status, stats, p, reference, recent):
    increase = episode["direction"] == "INCREASE"
    title = "Más uso registrado en este teléfono" if increase else "Menos uso registrado en este teléfono"
    reason = {
        "RESOLVED": "Cerramos este aviso. El promedio registrado ya no mantiene la diferencia que lo abrió.",
        "INCONCLUSIVE": "Seguimos observando; estos datos no alcanzan para confirmar ni cerrar el aviso.",
        "INSUFFICIENT_DATA": "No podemos actualizar la comparación: faltan datos verificados.",
        "CONTEXT_REVIEW": "No actualizamos la comparación porque cambió el contexto o falta verificar a quién corresponde.",
        "SERIES_CHANGED": "Este aviso corresponde a otra medición; no podemos seguir comparándolo.",
        "EXPIRED": "Terminó el período de seguimiento de este aviso. Eso no significa que el uso haya vuelto al nivel anterior.",
        "WITHDRAWN": "Retiramos este aviso: una corrección de los datos cambió la comparación que lo originó.",
    }.get(status)
    if status != "ACTIVE":
        title = "Actualización del aviso"
    numbers = None
    text = reason or ""
    if stats is not None:
        d = stats["delta"]
        sign = "más" if d > 0 else "menos" if d < 0 else "de diferencia"
        dates = f"{recent[0]['date']} al {recent[-1]['date']}"
        text = (f"Del {dates} se registraron {duration(stats['recent'])} por día en este teléfono; "
                f"en la referencia ({reference[0]['date']} al {reference[-1]['date']}), "
                f"{duration(stats['reference'])}. Son {duration(abs(d))} {sign} por día. " + (reason or "")).strip()
        numbers = {key: float(value) for key, value in stats.items()}
        numbers["percent_change"] = None if stats["reference"] == 0 else float(100*d/stats["reference"])
        # Al mostrar redondeo puede perderse una diferencia pequeña; conservar detalle exacto.
        numbers["observed_days_recent"] = numbers["observed_days_reference"] = 14
    recommendation = ("Podés conversar con tu hijo/a sobre qué cambió en la rutina y acordar juntos un momento para una actividad que disfruten."
                      if increase else "Pueden conversar sobre qué cambió en la rutina y qué acuerdos les resultan útiles.")
    return {"card_id": episode["card_id"], "profile_id": p["profile_id"], "series_id": episode["series_id"],
            "direction": episode["direction"], "status": status, "title": title, "text": text,
            "recommendation": recommendation, "statistics": numbers,
            "evaluation_date": p["evaluation_date"], "time_zone": episode["time_zone"],
            "opening_reference_start": episode["reference_start"], "opening_recent_start": episode["opening_start"],
            "comparison_recent_start": (parse_day(p["evaluation_date"])-timedelta(days=14)).isoformat(),
            "measurement": "uso registrado en este teléfono",
            "measurement_detail": "Duración de pantalla interactiva registrada por Android. No incluye otras pantallas ni identifica por sí sola quién usó el teléfono.",
            "configuration_id": VERSION, "configuration_fingerprint": CONFIG_FINGERPRINT,
            "scope": CONFIG["scope"], "delivery_status": "CANDIDATE_NOT_DELIVERED"}


def advance(state, p):
    """Transición pura. Se persiste junto con el recibo dentro de una transacción."""
    state = json.loads(canonical(state)) if state else {"episode": None, "created": [], "cooldown_until": None, "last_date": None}
    evaluation = parse_day(p["evaluation_date"])
    if state["last_date"] and evaluation < parse_day(state["last_date"]):
        raise MessageConflict("out_of_order_evaluation")
    days = {row["date"]: row for row in p["days"]}
    episode = state["episode"]
    recent = window(days, evaluation-timedelta(days=14))
    reference = window(days, evaluation-timedelta(days=28))
    stats = None
    status, action, card = "NO_CARD", "NONE", None
    guarded = p["assignment_verified"] and not p["shared_phone"] and not p["context_declared"]
    if episode:
        if episode["series_id"] != p["series_id"] or episode["time_zone"] != p["time_zone"]:
            status = "SERIES_CHANGED"
        elif not guarded:
            status = "CONTEXT_REVIEW"
        else:
            reference = window(days, parse_day(episode["reference_start"]))
            opening = window(days, parse_day(episode["opening_start"]))
            # Snapshot incluye siempre ambas ventanas de apertura, también tras correcciones.
            opening_stats = statistics(opening, reference)
            if opening_stats is None:
                status = "INSUFFICIENT_DATA"
            elif direction(opening_stats) != episode["direction"]:
                status = "WITHDRAWN"
            else:
                stats = statistics(recent, reference)
                if stats is None:
                    status = "INSUFFICIENT_DATA"
                else:
                    nonoverlap = evaluation-timedelta(days=14) >= parse_day(episode["opening_end"])
                    resolved = (stats["delta"] <= CONFIG["return_margin_minutes"] and stats["maximum"] <= CONFIG["return_margin_minutes"]
                                if episode["direction"] == "INCREASE" else
                                stats["delta"] >= -CONFIG["return_margin_minutes"] and stats["minimum"] >= -CONFIG["return_margin_minutes"])
                    status = "RESOLVED" if nonoverlap and resolved else "ACTIVE" if direction(stats) == episode["direction"] else "INCONCLUSIVE"
        # Vencimiento no equivale a recuperación, aun cuando faltan datos/contexto.
        if status not in {"SERIES_CHANGED", "WITHDRAWN", "RESOLVED"} and (evaluation-parse_day(episode["opened_date"])).days >= CONFIG["maximum_episode_days"]:
            status = "EXPIRED"
        card = make_card(episode, status, stats, p, reference, recent)
        action = "UPDATE"
        if status in {"RESOLVED", "SERIES_CHANGED", "WITHDRAWN", "EXPIRED"}:
            state["episode"] = None
            state["cooldown_until"] = (evaluation+timedelta(days=CONFIG["cooldown_days"])).isoformat()
    elif not guarded:
        status = "CONTEXT_REVIEW"
    elif not usable(recent) or not usable(reference):
        status = "INSUFFICIENT_DATA"
    else:
        stats = statistics(recent, reference)
        selected = direction(stats)
        count = sum(0 <= (evaluation-parse_day(d)).days < CONFIG["limit_period_days"] for d in state["created"])
        if state["cooldown_until"] and evaluation < parse_day(state["cooldown_until"]):
            status = "COOLDOWN"
        elif count >= CONFIG["maximum_new_cards"]:
            status = "CARD_LIMIT"
        elif selected:
            episode = {"card_id": digest([p["profile_id"], p["series_id"], p["evaluation_date"], VERSION, selected]),
                       "series_id": p["series_id"], "time_zone": p["time_zone"], "direction": selected,
                       "opened_date": p["evaluation_date"], "reference_start": reference[0]["date"],
                       "opening_start": recent[0]["date"], "opening_end": evaluation.isoformat()}
            state["episode"] = episode
            state["created"].append(evaluation.isoformat())
            card = make_card(episode, "ACTIVE", stats, p, reference, recent)
            action, status = "CREATE", "ACTIVE"
    state["last_date"] = evaluation.isoformat()
    return state, {"status": status, "action": action, "card": card,
                   "configuration": json.loads(canonical(CONFIG)), "c1_evidence_ids": p["c1_evidence_ids"],
                   "c1_role": CONFIG["c1_role"], "push_notification": False}


class AdultMessageService:
    """SQLite aislado del repositorio C1. Un evaluate es una transacción serial."""
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_absolute():
            raise ValueError("absolute_message_database_required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS states (profile TEXT PRIMARY KEY, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts (request TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evaluations (profile TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT NOT NULL, UNIQUE(profile,fingerprint));
                CREATE TABLE IF NOT EXISTS revisions (profile TEXT NOT NULL, series TEXT NOT NULL, day TEXT NOT NULL, revision INTEGER NOT NULL, content TEXT NOT NULL, PRIMARY KEY(profile,series,day,revision));
                CREATE TABLE IF NOT EXISTS cards (card TEXT NOT NULL, version INTEGER NOT NULL, profile TEXT NOT NULL, content TEXT NOT NULL, PRIMARY KEY(card,version));
            ''')
            existing = db.execute("SELECT fingerprint FROM config WHERE id=1").fetchone()
            if existing and existing[0] != CONFIG_FINGERPRINT:
                raise MessageConflict("configuration_changed_requires_new_store")
            db.execute("INSERT OR IGNORE INTO config VALUES(1,?)", (CONFIG_FINGERPRINT,))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def evaluate(self, payload):
        p = parse_payload(payload)
        if not self.check_ready():
            raise MessageUnavailable("adult_message_repository_unavailable")
        fingerprint = digest({k:v for k,v in p.items() if k != "request_id"})
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            original = db.execute("SELECT fingerprint,result FROM receipts WHERE request=?", (p["request_id"],)).fetchone()
            if original:
                if original[0] != fingerprint:
                    raise MessageConflict("request_content_conflict")
                result = json.loads(original[1]); result["replayed"] = True
                db.commit(); return result
            equivalent = db.execute("SELECT result FROM evaluations WHERE profile=? AND fingerprint=?", (p["profile_id"],fingerprint)).fetchone()
            if equivalent:
                result = json.loads(equivalent[0]); result["replayed"] = True
                db.execute("INSERT INTO receipts VALUES(?,?,?,?)", (p["request_id"],fingerprint,canonical(result),canonical(p)))
                db.commit(); return result
            corrected_dates = []
            for row in p["days"]:
                key = (p["profile_id"],p["series_id"],row["date"])
                previous = db.execute("SELECT revision,content FROM revisions WHERE profile=? AND series=? AND day=? ORDER BY revision DESC LIMIT 1", key).fetchone()
                content = canonical(row)
                if previous and (row["revision"] < previous[0] or (row["revision"] == previous[0] and previous[1] != content)):
                    raise MessageConflict("daily_revision_conflict")
                if previous and row["revision"] > previous[0]:
                    corrected_dates.append(row["date"])
                db.execute("INSERT OR IGNORE INTO revisions VALUES(?,?,?,?,?)", (*key,row["revision"],content))
            received_payload = canonical(p)
            # La base conserva las ventanas de apertura aunque un nuevo lote sólo traiga días nuevos.
            persisted = db.execute("SELECT content FROM revisions r WHERE profile=? AND series=? AND day<? AND revision=(SELECT MAX(revision) FROM revisions x WHERE x.profile=r.profile AND x.series=r.series AND x.day=r.day) ORDER BY day", (p["profile_id"],p["series_id"],p["evaluation_date"])).fetchall()
            p["days"] = [json.loads(row[0]) for row in persisted]
            old = db.execute("SELECT state FROM states WHERE profile=?", (p["profile_id"],)).fetchone()
            state, result = advance(json.loads(old[0]) if old else None, p)
            result["corrected_dates"] = corrected_dates
            result["historical_card_corrections"] = []
            terminal = {"RESOLVED", "WITHDRAWN", "EXPIRED", "SERIES_CHANGED", "CORRECTED_HISTORY"}
            latest_cards = db.execute("SELECT card,version,content FROM cards c WHERE profile=? AND version=(SELECT MAX(version) FROM cards x WHERE x.card=c.card)", (p["profile_id"],)).fetchall()
            days = {r["date"]:r for r in p["days"]}
            for card_id, version, encoded_card in latest_cards:
                previous_card = json.loads(encoded_card)
                if previous_card["series_id"] != p["series_id"] or previous_card["status"] not in terminal:
                    continue
                starts = [previous_card["opening_reference_start"], previous_card["opening_recent_start"], previous_card["comparison_recent_start"]]
                affected = any(parse_day(start) <= parse_day(day) < parse_day(start)+timedelta(days=14) for start in starts for day in corrected_dates)
                if not affected:
                    continue
                opening_stats = statistics(window(days,parse_day(starts[1])),window(days,parse_day(starts[0])))
                previous_card["status"] = "WITHDRAWN" if opening_stats is not None and direction(opening_stats) != previous_card["direction"] else "CORRECTED_HISTORY"
                previous_card["title"] = "Corrección del aviso"
                previous_card["text"] = "Una corrección cambió los datos de este aviso. Conservamos su historial y usamos los registros corregidos en las próximas evaluaciones."
                previous_card["statistics"] = None
                previous_card["corrected_dates"] = corrected_dates
                previous_card["updated_date"] = p["evaluation_date"]
                db.execute("INSERT INTO cards VALUES(?,?,?,?)", (card_id,version+1,p["profile_id"],canonical(previous_card)))
                result["historical_card_corrections"].append({"card_id":card_id,"version":version+1,"status":previous_card["status"]})
            if corrected_dates:
                old_stale = state.get("c1_stale_since")
                state["c1_stale_since"] = min(corrected_dates+[old_stale] if old_stale else corrected_dates)
            result["c1_correction_warning_since"] = state.get("c1_stale_since")
            result["replayed"] = False
            result["evaluation_id"] = fingerprint
            result["card_version"] = None
            if result["card"]:
                card = result["card"]
                prev = db.execute("SELECT version,content FROM cards WHERE card=? ORDER BY version DESC LIMIT 1", (card["card_id"],)).fetchone()
                if not prev or prev[1] != canonical(card):
                    version = prev[0]+1 if prev else 1
                    db.execute("INSERT INTO cards VALUES(?,?,?,?)", (card["card_id"],version,p["profile_id"],canonical(card)))
                else:
                    version = prev[0]
                result["card_version"] = version
            db.execute("INSERT OR REPLACE INTO states VALUES(?,?)", (p["profile_id"],canonical(state)))
            encoded = canonical(result)
            db.execute("INSERT INTO receipts VALUES(?,?,?,?)", (p["request_id"],fingerprint,encoded,received_payload))
            db.execute("INSERT INTO evaluations VALUES(?,?,?)", (p["profile_id"],fingerprint,encoded))
            db.commit(); return result
        except sqlite3.Error:
            db.rollback()
            raise MessageUnavailable("adult_message_repository_unavailable") from None
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    def history(self, profile_id):
        identifier(profile_id)
        if not self.check_ready():
            raise MessageUnavailable("adult_message_repository_unavailable")
        try:
            with closing(self.connect()) as db, db:
                rows = db.execute("SELECT version,content FROM cards WHERE profile=? ORDER BY rowid", (profile_id,)).fetchall()
        except sqlite3.Error:
            raise MessageUnavailable("adult_message_repository_unavailable") from None
        return [{"version":v, "card":json.loads(c)} for v,c in rows]

    def check_ready(self):
        if not self.path.is_file():
            return False
        from urllib.parse import quote
        try:
            with closing(sqlite3.connect("file:"+quote(str(self.path))+"?mode=ro", uri=True, timeout=1)) as db:
                saved = db.execute("SELECT fingerprint FROM config WHERE id=1").fetchone()
                for table in ("states", "receipts", "evaluations", "revisions", "cards"):
                    db.execute("SELECT 1 FROM "+table+" LIMIT 1").fetchone()
                return bool(saved and saved[0] == CONFIG_FINGERPRINT)
        except sqlite3.Error:
            return False
