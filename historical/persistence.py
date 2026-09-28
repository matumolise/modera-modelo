"""Contratos de persistencia para el análisis histórico de Moderá."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import os

from .analyzer import HistoricalAnalysisResult, HistoricalAnalyzerState
from .contracts import Coverage, HistoricalRepresentation, ObservationStatus, Provenance
from .detector import C1_DETECTOR_FAMILY, C1DetectorConfig, CusumState
from .receipts import deserialize_analysis_result, serialize_analysis_result


@dataclass(frozen=True)
class HistoricalStreamKey:
    """Identifica un stream histórico con una configuración analítica concreta."""

    subject_id: str
    representation_spec_id: str
    detector_family: str
    detector_k: float
    threshold: float
    detector_min_history: int
    analysis_version: str

    def __post_init__(self) -> None:
        if not self.subject_id.strip():
            raise ValueError("subject_id no puede estar vacío.")

        if not self.representation_spec_id.strip():
            raise ValueError("representation_spec_id no puede estar vacío.")

        if not self.detector_family.strip():
            raise ValueError("detector_family no puede estar vacío.")

        if not self.analysis_version.strip():
            raise ValueError("analysis_version no puede estar vacío.")

    @classmethod
    def from_c1(
        cls,
        subject_id: str,
        representation_spec_id: str,
        config: C1DetectorConfig,
        analysis_version: str,
    ) -> "HistoricalStreamKey":
        """Construye la identidad del stream a partir de una configuración C1."""

        return cls(
            subject_id=subject_id,
            representation_spec_id=representation_spec_id,
            detector_family=C1_DETECTOR_FAMILY,
            detector_k=float(config.k),
            threshold=float(config.threshold),
            detector_min_history=config.min_history,
            analysis_version=analysis_version,
        )

def serialize_analyzer_state(
    state: HistoricalAnalyzerState,
) -> dict[str, float | None]:
    """Convierte el estado del analizador a una representación persistible."""

    return {
        "positive_cusum": float(state.cusum_state.positive),
        "negative_cusum": float(state.cusum_state.negative),
        "previous_eligible_statistic": (
            None
            if state.previous_eligible_statistic is None
            else float(state.previous_eligible_statistic)
        ),
    }


def deserialize_analyzer_state(
    payload: dict[str, float | None],
) -> HistoricalAnalyzerState:
    """Reconstruye el estado del analizador desde su representación persistida."""

    return HistoricalAnalyzerState(
        cusum_state=CusumState(
            positive=payload["positive_cusum"],
            negative=payload["negative_cusum"],
        ),
        previous_eligible_statistic=payload[
            "previous_eligible_statistic"
        ],
    )

class FileHistoricalStateStore:
    """Persistencia local simple del estado de streams históricos."""

    FORMAT_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @staticmethod
    def _stream_id(key: HistoricalStreamKey) -> str:
        """Construye una identidad estable y reversible para el stream."""

        return json.dumps(
            asdict(key),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _read_document(self) -> dict:
        if not self.path.exists():
            return {
                "format_version": self.FORMAT_VERSION,
                "streams": {},
            }

        with self.path.open("r", encoding="utf-8") as file:
            document = json.load(file)

        if document.get("format_version") != self.FORMAT_VERSION:
            raise ValueError(
                "La versión del archivo de estado histórico no es compatible."
            )

        streams = document.get("streams")
        if not isinstance(streams, dict):
            raise ValueError(
                "El archivo de estado histórico no contiene streams válidos."
            )

        return document

    def save(
        self,
        key: HistoricalStreamKey,
        state: HistoricalAnalyzerState,
    ) -> None:
        """Guarda el estado actual de un stream sin reemplazar los demás."""

        document = self._read_document()
        stream_id = self._stream_id(key)

        document["streams"][stream_id] = {
            "key": asdict(key),
            "state": serialize_analyzer_state(state),
        }

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open("w", encoding="utf-8") as file:
            json.dump(
                document,
                file,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

    def load(
        self,
        key: HistoricalStreamKey,
    ) -> HistoricalAnalyzerState:
        """Recupera el estado del stream o devuelve su estado inicial."""

        document = self._read_document()
        stored = document["streams"].get(
            self._stream_id(key)
        )

        if stored is None:
            return HistoricalAnalyzerState()

        if stored.get("key") != asdict(key):
            raise ValueError(
                "La identidad persistida del stream no coincide con la solicitada."
            )

        state_payload = stored.get("state")
        if not isinstance(state_payload, dict):
            raise ValueError(
                "El stream histórico no contiene un estado válido."
            )

        return deserialize_analyzer_state(
            state_payload
        )

def serialize_historical_representation(
    representation: HistoricalRepresentation,
) -> dict:
    """Convierte una representación histórica a un formato persistible."""

    return {
        "representation_record_id": representation.representation_record_id,
        "representation_spec_id": representation.representation_spec_id,
        "subject_id": representation.subject_id,
        "phenomenon": representation.phenomenon,
        "interval_start": representation.interval_start.isoformat(),
        "interval_end": representation.interval_end.isoformat(),
        "value": representation.value,
        "unit": representation.unit,
        "status": representation.status.value,
        "coverage": {
            "value": representation.coverage.value,
            "basis": representation.coverage.basis,
        },
        "quality_flags": list(representation.quality_flags),
        "provenance": {
            "source_id": representation.provenance.source_id,
            "source_version": representation.provenance.source_version,
            "source_semantics": representation.provenance.source_semantics,
            "adapter_version": representation.provenance.adapter_version,
            "input_fingerprint": representation.provenance.input_fingerprint,
        },
        "computed_at": representation.computed_at.isoformat(),
    }


def deserialize_historical_representation(
    payload: dict,
) -> HistoricalRepresentation:
    """Reconstruye una representación histórica desde datos persistidos."""

    coverage_payload = payload["coverage"]
    provenance_payload = payload["provenance"]

    return HistoricalRepresentation(
        representation_record_id=payload["representation_record_id"],
        representation_spec_id=payload["representation_spec_id"],
        subject_id=payload["subject_id"],
        phenomenon=payload["phenomenon"],
        interval_start=datetime.fromisoformat(payload["interval_start"]),
        interval_end=datetime.fromisoformat(payload["interval_end"]),
        value=payload["value"],
        unit=payload["unit"],
        status=ObservationStatus(payload["status"]),
        coverage=Coverage(
            value=coverage_payload["value"],
            basis=coverage_payload["basis"],
        ),
        quality_flags=tuple(payload["quality_flags"]),
        provenance=Provenance(
            source_id=provenance_payload["source_id"],
            source_version=provenance_payload["source_version"],
            source_semantics=provenance_payload["source_semantics"],
            adapter_version=provenance_payload["adapter_version"],
            input_fingerprint=provenance_payload["input_fingerprint"],
        ),
        computed_at=datetime.fromisoformat(payload["computed_at"]),
    )


class FileHistoricalRepresentationStore:
    """Persistencia local del historial de representaciones."""

    FORMAT_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _read_document(self) -> dict:
        if not self.path.exists():
            return {
                "format_version": self.FORMAT_VERSION,
                "representations": [],
            }

        with self.path.open("r", encoding="utf-8") as file:
            document = json.load(file)

        if document.get("format_version") != self.FORMAT_VERSION:
            raise ValueError(
                "La versión del historial persistido no es compatible."
            )

        representations = document.get("representations")
        if not isinstance(representations, list):
            raise ValueError(
                "El archivo histórico no contiene representaciones válidas."
            )

        return document

    def append(
        self,
        representation: HistoricalRepresentation,
    ) -> bool:
        """Agrega un registro si su identidad todavía no fue persistida."""

        document = self._read_document()
        serialized = serialize_historical_representation(
            representation
        )

        for stored in document["representations"]:
            if (
                stored.get("representation_record_id")
                == representation.representation_record_id
            ):
                if stored != serialized:
                    raise ValueError(
                        "representation_record_id ya existe con contenido diferente."
                    )
                return False

        document["representations"].append(serialized)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open("w", encoding="utf-8") as file:
            json.dump(
                document,
                file,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

        return True

    def load_history(
        self,
        *,
        subject_id: str,
        representation_spec_id: str,
    ) -> list[HistoricalRepresentation]:
        """Recupera el historial del sujeto y representación en orden temporal."""

        document = self._read_document()

        history = [
            deserialize_historical_representation(payload)
            for payload in document["representations"]
            if payload.get("subject_id") == subject_id
            and payload.get("representation_spec_id")
            == representation_spec_id
        ]

        return sorted(
            history,
            key=lambda item: (
                item.interval_start,
                item.interval_end,
                item.representation_record_id,
            ),
        )

class FileHistoricalRepository:
    """Historial, estado y recibos en un archivo; requiere un único escritor.

    El reemplazo atómico evita publicar progreso parcial. No serializa
    procesamientos concurrentes ni promete durabilidad ante todo fallo físico.
    """

    FORMAT_VERSION = 3

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _empty_document(self) -> dict:
        return {
            "format_version": self.FORMAT_VERSION,
            "representations": [],
            "streams": {},
            "receipts": {},
            "records_without_receipt": {},
            "receipts_required": False,
        }

    def _read_document(self) -> dict:
        if not self.path.exists():
            return self._empty_document()

        with self.path.open("r", encoding="utf-8") as file:
            document = json.load(file)

        if document.get("format_version") not in (1, 2, self.FORMAT_VERSION):
            raise ValueError(
                "La versión del repositorio histórico no es compatible."
            )

        if not isinstance(document.get("representations"), list):
            raise ValueError(
                "El repositorio histórico no contiene representaciones válidas."
            )

        if not isinstance(document.get("streams"), dict):
            raise ValueError(
                "El repositorio histórico no contiene streams válidos."
            )

        original_version = document["format_version"]
        if original_version == 1:
            document["receipts"] = {}
        if not isinstance(document.get("receipts"), dict):
            raise ValueError("El repositorio histórico no contiene recibos válidos.")

        if original_version in (1, 2):
            # Migración en memoria: una lectura no modifica el archivo.
            # v2 no registraba activación; no permite demostrar el origen de
            # un registro sin recibo. No se lo declara automáticamente legado.
            document["records_without_receipt"] = {
                item["representation_record_id"]: (
                    "legacy" if original_version == 1 else "unclassified"
                )
                for item in document["representations"]
                if item["representation_record_id"] not in document["receipts"]
            }
            document["receipts_required"] = original_version == 2
            document["format_version"] = self.FORMAT_VERSION

        exemptions = document.get("records_without_receipt")
        if (not isinstance(exemptions, dict)
                or type(document.get("receipts_required")) is not bool
                or any(value not in ("legacy", "unclassified")
                       for value in exemptions.values())):
            raise ValueError("La política de integridad de recibos no es válida.")
        record_ids = {item["representation_record_id"]
                      for item in document["representations"]}
        receipt_ids = set(document["receipts"])
        if (record_ids != receipt_ids | set(exemptions)
                or receipt_ids & set(exemptions)
                or (receipt_ids and not document["receipts_required"])):
            raise ValueError("Falla de integridad: representación o recibo sin asociación válida.")

        return document

    @staticmethod
    def _stream_id(key: HistoricalStreamKey) -> str:
        return json.dumps(
            asdict(key),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _write_document(self, document: dict) -> None:
        """Publica una nueva versión completa mediante reemplazo atómico."""

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self.path.with_name(
            f".{self.path.name}.tmp"
        )

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    document,
                    file,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                file.flush()
                os.fsync(file.fileno())

            os.replace(
                temporary_path,
                self.path,
            )
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def save_analysis_progress(
        self,
        *,
        representation: HistoricalRepresentation,
        stream_key: HistoricalStreamKey,
        state: HistoricalAnalyzerState,
        result: HistoricalAnalysisResult | None = None,
        emitter_version: str | None = None,
    ) -> bool:
        """Guarda el progreso y, si se suministra, su resultado en un solo reemplazo."""

        if representation.subject_id != stream_key.subject_id:
            raise ValueError(
                "La representación y el stream pertenecen a sujetos diferentes."
            )

        if (
            representation.representation_spec_id
            != stream_key.representation_spec_id
        ):
            raise ValueError(
                "La representación y el stream usan especificaciones diferentes."
            )

        document = self._read_document()
        serialized = serialize_historical_representation(
            representation
        )

        if result is not None:
            if not emitter_version or not emitter_version.strip():
                raise ValueError("El recibo requiere emitter_version.")
            if state != result.next_state:
                raise ValueError("El estado no coincide con el resultado del recibo.")
            self._validate_result(representation, stream_key, emitter_version, result)
            original = self._load_receipt(
                document, representation, stream_key, emitter_version,
            )
            if original is not None:
                if serialize_analysis_result(original) != serialize_analysis_result(result):
                    raise ValueError("El recibo ya existe con un resultado diferente.")
                return False
        elif emitter_version is not None:
            raise ValueError("emitter_version requiere un resultado para el recibo.")

        if result is None and document["receipts_required"]:
            raise ValueError("Falla de integridad: el repositorio activado requiere un recibo.")

        representation_added = True

        for stored in document["representations"]:
            if (
                stored.get("representation_record_id")
                == representation.representation_record_id
            ):
                if stored != serialized:
                    raise ValueError(
                        "representation_record_id ya existe "
                        "con contenido diferente."
                    )

                representation_added = False
                break

        stream_id = self._stream_id(stream_key)
        serialized_state = serialize_analyzer_state(state)

        if not representation_added:
            if result is not None:
                raise ValueError("La representación ya fue procesada sin recibo recuperable.")
            stored_stream = document["streams"].get(stream_id)

            if stored_stream is None:
                raise ValueError(
                    "La representación ya existe, pero no tiene "
                    "un estado analítico asociado."
                )

            if (
                stored_stream.get("key") != asdict(stream_key)
                or stored_stream.get("state") != serialized_state
            ):
                raise ValueError(
                    "La representación ya fue procesada con "
                    "un estado analítico diferente."
                )

            return False

        document["representations"].append(serialized)

        previous_state = document["streams"].get(stream_id, {}).get(
            "state", serialize_analyzer_state(HistoricalAnalyzerState()),
        )
        document["streams"][stream_id] = {
            "key": asdict(stream_key),
            "state": serialized_state,
        }

        if result is not None:
            document["receipts"][representation.representation_record_id] = {
                "stream_key": asdict(stream_key),
                "emitter_version": emitter_version,
                "result": serialize_analysis_result(result),
                "previous_state": previous_state,
            }
            document["receipts_required"] = True
        else:
            # Compatibilidad del API de bajo nivel antes de activar recibos.
            document["records_without_receipt"][representation.representation_record_id] = "legacy"

        self._write_document(document)

        return True

    @staticmethod
    def _validate_result(representation, stream_key, emitter_version, result) -> None:
        evaluation = result.evaluation
        expected = {
            "subject_id": representation.subject_id,
            "representation_record_id": representation.representation_record_id,
            "representation_spec_id": representation.representation_spec_id,
            "evaluated_interval_start": representation.interval_start,
            "evaluated_interval_end": representation.interval_end,
            "analysis_version": stream_key.analysis_version,
            "detector_family": stream_key.detector_family,
            "detector_k": stream_key.detector_k,
            "threshold": stream_key.threshold,
            "detector_min_history": stream_key.detector_min_history,
            "reference_location": result.reference.location,
            "reference_scale": result.reference.scale,
            "reference_history_count": result.reference.history_count,
            "reference_cutoff": result.reference.reference_cutoff,
        }
        if any(getattr(evaluation, name) != value for name, value in expected.items()):
            raise ValueError("El resultado del recibo no coincide con su entrada o referencia.")
        event = result.emission.event
        if event is not None:
            names = (
                "evaluation_id", "subject_id", "representation_record_id",
                "representation_spec_id", "evaluated_interval_start",
                "evaluated_interval_end", "detector_family", "detector_statistic",
                "threshold",
            )
            if event.emitter_version != emitter_version or any(
                getattr(event, name) != getattr(evaluation, name) for name in names
            ):
                raise ValueError("El evento del recibo no coincide con su evaluación.")

    def _load_receipt(
        self, document: dict, representation: HistoricalRepresentation,
        stream_key: HistoricalStreamKey, emitter_version: str,
    ) -> HistoricalAnalysisResult | None:
        receipt = document["receipts"].get(representation.representation_record_id)
        if receipt is None:
            status = document["records_without_receipt"].get(
                representation.representation_record_id,
            )
            if status == "legacy":
                raise ValueError("La representación legada fue procesada sin recibo recuperable.")
            if status == "unclassified":
                raise ValueError("Registro v2 sin recibo: origen no clasificable automáticamente.")
            return None
        stored = next((item for item in document["representations"]
                       if item["representation_record_id"]
                       == representation.representation_record_id), None)
        if stored is None:
            raise ValueError("El recibo no tiene una representación asociada.")
        incoming = serialize_historical_representation(representation)
        # La fecha de cálculo puede cambiar al reconstruir el mismo dato.
        # Se conserva el registro original; los demás campos deben coincidir.
        stored_input = {name: value for name, value in stored.items()
                        if name != "computed_at"}
        incoming.pop("computed_at")
        if stored_input != incoming:
            raise ValueError("Reintento incompatible: representación con contenido diferente.")
        if (receipt["stream_key"] != asdict(stream_key)
                or receipt["emitter_version"] != emitter_version):
            raise ValueError("Reintento incompatible: stream o versión del emisor diferente.")
        result = deserialize_analysis_result(receipt["result"])
        self._validate_result(representation, stream_key, emitter_version, result)
        return result

    def load_analysis_result(
        self, *, representation: HistoricalRepresentation,
        stream_key: HistoricalStreamKey, emitter_version: str,
    ) -> HistoricalAnalysisResult | None:
        """Recupera el resultado original para una entrada compatible, sin escribir."""
        return self._load_receipt(
            self._read_document(), representation, stream_key, emitter_version,
        )

    def contains_representation(
        self,
        representation_record_id: str,
    ) -> bool:
        """Indica si una representación ya fue persistida por su identificador."""

        if not representation_record_id.strip():
            raise ValueError(
                "representation_record_id no puede estar vacío."
            )

        document = self._read_document()

        return any(
            stored.get("representation_record_id")
            == representation_record_id
            for stored in document["representations"]
        )

    def load_history(
        self,
        *,
        subject_id: str,
        representation_spec_id: str,
    ) -> list[HistoricalRepresentation]:
        """Recupera el historial persistido en orden temporal."""

        document = self._read_document()

        history = [
            deserialize_historical_representation(payload)
            for payload in document["representations"]
            if payload.get("subject_id") == subject_id
            and payload.get("representation_spec_id")
            == representation_spec_id
        ]

        return sorted(
            history,
            key=lambda item: (
                item.interval_start,
                item.interval_end,
                item.representation_record_id,
            ),
        )

    def load_state(
        self,
        key: HistoricalStreamKey,
    ) -> HistoricalAnalyzerState:
        """Recupera el estado persistido o devuelve el estado inicial."""

        document = self._read_document()
        stored = document["streams"].get(
            self._stream_id(key)
        )

        if stored is None:
            return HistoricalAnalyzerState()

        if stored.get("key") != asdict(key):
            raise ValueError(
                "La identidad persistida del stream "
                "no coincide con la solicitada."
            )

        state_payload = stored.get("state")

        if not isinstance(state_payload, dict):
            raise ValueError(
                "El stream histórico no contiene un estado válido."
            )

        return deserialize_analyzer_state(state_payload)