"""Adaptador HTTP del C1 publicado; no interpreta ni envía alertas."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import os
import tempfile
import threading
from uuid import uuid4

from historical.adapters import (DAILY_USE_DURATION_ADAPTER_VERSION,
                                 DAILY_USE_DURATION_PHENOMENON, DAILY_USE_DURATION_SPEC_ID)
from historical.contracts import Coverage, HistoricalRepresentation, ObservationStatus, Provenance
from historical.persistence import (FileHistoricalRepository, HistoricalStreamKey,
                                   deserialize_analyzer_state)
from historical.receipts import serialize_analysis_result
from historical.receipts import deserialize_analysis_result
from historical.analyzer import HistoricalAnalyzerState
from historical.detector import DetectorEvaluationOutcome
from historical.service import process_c1_representation

from .historical_config import HISTORICAL_API_VERSION, HistoricalProfile, identifier
from .json_codec import strict_json
from .writer_lease import WriterLease


class InvalidHistoricalRequest(ValueError):
    pass


class HistoricalConflict(ValueError):
    pass


class HistoricalUnavailable(RuntimeError):
    pass


def _text(value, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError("Texto invalido")
    return value


def _date(value):
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("Fecha invalida")
    result = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Fecha sin zona horaria")
    return result.astimezone(timezone.utc)


def parse_representation(value):
    keys = {"representation_record_id", "representation_spec_id", "subject_id", "phenomenon",
            "interval_start", "interval_end", "value", "unit", "status", "coverage",
            "quality_flags", "provenance", "computed_at"}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("Contrato de representacion incompleto o desconocido")
    if (value["representation_spec_id"] != DAILY_USE_DURATION_SPEC_ID
            or value["phenomenon"] != DAILY_USE_DURATION_PHENOMENON or value["unit"] != "minutes"):
        raise ValueError("Solo se admite la representacion v2 publicada en minutos")
    status = ObservationStatus(value["status"])
    number = value["value"]
    if status in {ObservationStatus.MISSING, ObservationStatus.NOT_APPLICABLE}:
        if number is not None:
            raise ValueError("Ausencia requiere null")
    elif (type(number) not in (int, float) or not math.isfinite(float(number)) or number < 0):
        raise ValueError("Duracion invalida")
    coverage = value["coverage"]
    if not isinstance(coverage, dict) or set(coverage) != {"value", "basis"}:
        raise ValueError("Cobertura invalida")
    covered = coverage["value"]
    if covered is not None and (type(covered) not in (int, float)
                               or not math.isfinite(float(covered)) or not 0 <= covered <= 1):
        raise ValueError("Cobertura fuera de rango")
    flags = value["quality_flags"]
    if not isinstance(flags, list) or len(flags) > 64:
        raise ValueError("Flags invalidos")
    for flag in flags:
        _text(flag)
    provenance = value["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {
        "source_id", "source_version", "source_semantics", "adapter_version", "input_fingerprint"
    }:
        raise ValueError("Procedencia incompleta")
    if provenance["adapter_version"] != DAILY_USE_DURATION_ADAPTER_VERSION:
        raise ValueError("Version del adaptador incompatible")
    return HistoricalRepresentation(
        representation_record_id=identifier(value["representation_record_id"]),
        representation_spec_id=DAILY_USE_DURATION_SPEC_ID, subject_id=identifier(value["subject_id"]),
        phenomenon=DAILY_USE_DURATION_PHENOMENON, interval_start=_date(value["interval_start"]),
        interval_end=_date(value["interval_end"]), value=number, unit="minutes", status=status,
        coverage=Coverage(covered, _text(coverage["basis"], optional=True)), quality_flags=tuple(flags),
        provenance=Provenance(_text(provenance["source_id"]),
                              _text(provenance["source_version"], optional=True),
                              _text(provenance["source_semantics"], optional=True),
                              DAILY_USE_DURATION_ADAPTER_VERSION,
                              _text(provenance["input_fingerprint"], optional=True)),
        computed_at=_date(value["computed_at"]),
    )


def parse_historical_request(request):
    try:
        if not isinstance(request, dict) or set(request) != {"request_id", "representation"}:
            raise ValueError("Campos no admitidos")
        return identifier(request["request_id"]), parse_representation(request["representation"])
    except (ValueError, TypeError, OverflowError) as exc:
        raise InvalidHistoricalRequest("Solicitud historica invalida") from exc


class BoundHistoricalRepository(FileHistoricalRepository):
    """Formato v3 publicado con un vínculo de configuración adicional.

    No importa automáticamente repositorios previos sin vínculo. Se usa el
    mismo reemplazo atómico del núcleo para representación, recibo y estado.
    """

    def __init__(self, path, profile):
        super().__init__(path)
        self.profile = profile

    @property
    def initialized_path(self):
        return self.path.with_name(self.path.name + ".initialized")

    def mark_initialized(self):
        marker = b"historical-http-v1-candidate\n"
        if self.initialized_path.exists():
            if self.initialized_path.read_bytes() != marker:
                raise ValueError("Marca de inicializacion incompatible")
        else:
            with self.initialized_path.open("xb") as stream:
                stream.write(marker)
                stream.flush()
                os.fsync(stream.fileno())

    def _empty_document(self):
        document = super()._empty_document()
        document["analytics_binding"] = self.profile.binding
        return document

    def _read_document(self):
        if not self.path.exists():
            return self._empty_document()
        document = strict_json(self.path.read_bytes())
        self._validate_document(document)
        return document

    def _validate_document(self, document):
        keys = {"format_version", "representations", "streams", "receipts",
                "records_without_receipt", "receipts_required", "analytics_binding"}
        if (not isinstance(document, dict) or set(document) != keys
                or type(document["format_version"]) is not int
                or document["format_version"] != self.FORMAT_VERSION
                or document["analytics_binding"] != self.profile.binding):
            raise ValueError("Repositorio o vinculo de configuracion incompatible")
        if (not isinstance(document["representations"], list) or not isinstance(document["streams"], dict)
                or not isinstance(document["receipts"], dict) or document["records_without_receipt"] != {}
                or type(document["receipts_required"]) is not bool):
            raise ValueError("Estructura del repositorio invalida")
        records = [parse_representation(item) for item in document["representations"]]
        ids = [r.representation_record_id for r in records]
        if (len(set(ids)) != len(ids) or set(ids) != set(document["receipts"])
                or bool(records) != document["receipts_required"]):
            raise ValueError("Integridad de representaciones y recibos invalida")
        expected_streams = {}
        for record in records:
            key = self.stream_key(record)
            receipt = document["receipts"][record.representation_record_id]
            if not isinstance(receipt, dict) or set(receipt) != {
                "stream_key", "emitter_version", "result", "previous_state"
            }:
                raise ValueError("Recibo invalido")
            if receipt["stream_key"] != asdict(key) or receipt["emitter_version"] != self.profile.emitter_version:
                raise ValueError("Recibo de otra configuracion")
            result = deserialize_analysis_result(receipt["result"])
            self._validate_result(record, key, self.profile.emitter_version, result)
            previous = deserialize_analyzer_state(receipt["previous_state"])
            sid = self._stream_id(key)
            preceding = expected_streams.get(sid)
            expected_previous = (deserialize_analysis_result(preceding["result"]).next_state
                                 if preceding else HistoricalAnalyzerState())
            if previous != expected_previous:
                raise ValueError("Cadena de estados de recibos incompatible")
            if preceding and record.interval_start < _date(preceding["result"]["evaluation"]["evaluated_interval_end"]):
                raise ValueError("Orden temporal persistido incompatible")
            evaluation = result.evaluation
            if evaluation.outcome is DetectorEvaluationOutcome.ABSTAIN:
                if result.next_state != previous:
                    raise ValueError("Una abstencion altero el estado persistido")
            elif (result.next_state.cusum_state.positive != evaluation.positive_cusum
                  or result.next_state.cusum_state.negative != evaluation.negative_cusum
                  or result.next_state.previous_eligible_statistic != evaluation.detector_statistic):
                raise ValueError("Estado siguiente y evaluacion incompatibles")
            expected_streams[sid] = receipt
        if set(document["streams"]) != set(expected_streams):
            raise ValueError("Streams sin asociacion valida")
        for sid, last_receipt in expected_streams.items():
            stored = document["streams"][sid]
            if not isinstance(stored, dict) or set(stored) != {"key", "state"}:
                raise ValueError("Stream invalido")
            if stored["key"] != last_receipt["stream_key"]:
                raise ValueError("Identidad del stream invalida")
            state = deserialize_analyzer_state(stored["state"])
            if state != deserialize_analysis_result(last_receipt["result"]).next_state:
                raise ValueError("Estado final incompatible con el ultimo recibo")

    def stream_key(self, current):
        return HistoricalStreamKey.from_c1(current.subject_id, current.representation_spec_id,
                                            self.profile.config, self.profile.analysis_version)

    def _write_document(self, document):
        # Rechazar números no finitos antes de reemplazar el archivo anterior.
        json.dumps(document, allow_nan=False)
        self._validate_document(document)
        super()._write_document(document)
        self.mark_initialized()
        if os.name == "posix":
            fd = os.open(self.path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)


class HistoricalRuntime:
    def __init__(self, settings):
        self.ready = False
        self._lock = threading.Lock()
        self._lease = None
        try:
            self.profile = HistoricalProfile.load(settings.historical_config_path)
            path = settings.historical_repository_path.resolve()
            config_path = settings.historical_config_path.resolve()
            reserved = {path, path.with_name("." + path.name + ".tmp"),
                        path.with_name(path.name + ".writer.lock"),
                        path.with_name(path.name + ".initialized")}
            if config_path in reserved:
                raise ValueError("Perfil y archivos del repositorio se superponen")
            self._lease = WriterLease(path.with_name(path.name + ".writer.lock"))
            self.repository = BoundHistoricalRepository(path, self.profile)
            if self.repository.initialized_path.exists() and not path.is_file():
                raise ValueError("Falta un repositorio previamente inicializado")
            self.repository._read_document()
            self._expect_existing = path.exists()
            if path.exists():
                with path.open("r+b"):
                    pass
                self.repository.mark_initialized()
            # Comprobar escritura en el directorio sin crear un historial ficticio.
            with tempfile.TemporaryFile(dir=path.parent) as probe:
                probe.write(b"probe")
                probe.flush()
                os.fsync(probe.fileno())
            self.ready = True
        except Exception as exc:
            if self._lease is not None:
                self._lease.close()
            raise HistoricalUnavailable("No se pudo iniciar el historico") from exc

    def close(self):
        with self._lock:
            self.ready = False
            if self._lease is not None:
                self._lease.close()
                self._lease = None

    def _check_storage(self):
        if not self._lease or not self._lease.valid():
            raise ValueError("Reserva del escritor perdida")
        if self._expect_existing and not self.repository.path.is_file():
            raise ValueError("Repositorio previamente inicializado ausente")
        if self.repository.initialized_path.exists():
            self.repository.mark_initialized()  # Valida la marca; no la reescribe.
            if not self.repository.path.is_file():
                raise ValueError("Repositorio inicializado ausente")
        self.repository._read_document()

    def check_ready(self):
        with self._lock:
            if not self.ready:
                return False
            try:
                self._check_storage()
            except Exception:
                self.ready = False
            return self.ready

    def evaluate(self, request_id, current):
        with self._lock:
            if not self.ready:
                raise HistoricalUnavailable("Historico no disponible")
            try:
                # Validación del archivo y lectura-reintento-análisis-escritura
                # quedan dentro de la misma sección crítica para TODOS los sujetos.
                self._check_storage()
                key = self.repository.stream_key(current)
                if self.repository.contains_representation(current.representation_record_id):
                    try:
                        result = self.repository.load_analysis_result(
                            representation=current, stream_key=key,
                            emitter_version=self.profile.emitter_version,
                        )
                    except ValueError as exc:
                        raise HistoricalConflict("representation_conflict") from exc
                    replayed = True
                else:
                    history = self.repository.load_history(subject_id=current.subject_id,
                                                           representation_spec_id=current.representation_spec_id)
                    if history and current.interval_start < history[-1].interval_end:
                        raise HistoricalConflict("historical_order_conflict")
                    now = datetime.now(timezone.utc)
                    result = process_c1_representation(
                        repository=self.repository, current=current, stream_key=key,
                        config=self.profile.config, evaluation_id="eval-" + uuid4().hex,
                        event_id="event-" + uuid4().hex, analysis_version=self.profile.analysis_version,
                        emitter_version=self.profile.emitter_version, computed_at=now, emitted_at=now,
                    )
                    replayed = False
                    self._expect_existing = True
                serialized = serialize_analysis_result(result)
                json.dumps(serialized, allow_nan=False)
                return {"status": "processed", "request_id": request_id, "replayed": replayed,
                        "historical_api_version": HISTORICAL_API_VERSION,
                        "configuration_id": self.profile.configuration_id,
                        "configuration_fingerprint": self.profile.fingerprint,
                        "scope": "internal_technical_candidate", "result": serialized}
            except HistoricalConflict:
                raise
            except Exception as exc:
                self.ready = False
                raise HistoricalUnavailable("Fallo del repositorio o del procesamiento") from exc
