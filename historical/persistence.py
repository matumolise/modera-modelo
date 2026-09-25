"""Contratos de persistencia para el análisis histórico de Moderá."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import os

from .analyzer import HistoricalAnalyzerState
from .contracts import Coverage, HistoricalRepresentation, ObservationStatus, Provenance
from .detector import C1_DETECTOR_FAMILY, C1DetectorConfig, CusumState


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
    """Persistencia conjunta del historial y del estado analítico."""

    FORMAT_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _empty_document(self) -> dict:
        return {
            "format_version": self.FORMAT_VERSION,
            "representations": [],
            "streams": {},
        }

    def _read_document(self) -> dict:
        if not self.path.exists():
            return self._empty_document()

        with self.path.open("r", encoding="utf-8") as file:
            document = json.load(file)

        if document.get("format_version") != self.FORMAT_VERSION:
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
    ) -> bool:
        """Guarda representación y estado como una única versión persistida."""

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

        document["streams"][stream_id] = {
            "key": asdict(stream_key),
            "state": serialized_state,
        }

        self._write_document(document)

        return True

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