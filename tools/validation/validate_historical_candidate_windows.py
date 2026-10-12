"""Valida el candidato en Windows en entorno, datos y contenedor separados.

Usar Python 3.10 del entorno original. No crea commits ni publica cambios.
El histórico sólo usa SMOKE_ONLY no calibrado. Si existen los originales HU v1,
comprueba su carga y HTTP en Windows/Docker sin entrenarlos o modificarlos.
"""

import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def port_available(port):
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", port))


def pinned_requirements(path):
    """Versiones directas exactas, incluidas las referencias -r locales."""
    pins = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            included = pinned_requirements(path.parent / line[3:].strip())
        else:
            require(line.count("==") == 1, "Dependencia sin version exacta: " + line)
            name, version = line.split("==")
            included = {name: version}
        for name, version in included.items():
            require(name not in pins or pins[name] == version, "Versiones contradictorias: " + name)
            pins[name] = version
    return pins


def wait_http(process, url, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError("El servidor termino durante el arranque; revisar sus logs")
        try:
            with urllib.request.urlopen(url + "/health", timeout=1) as response:
                if response.code == 200:
                    return
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError("El servicio no estuvo READY dentro del tiempo previsto")


def run(args):
    require(os.name == "nt", "Este ejecutor es para Windows; usar las pruebas Linux documentadas")
    require(sys.version_info[:2] == (3, 10), "Ejecutar con el Python 3.10 del entorno original")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    state = (args.state_root or Path.home() / "Documents" / ("modera_historical_smoke_" + run_id)).resolve()
    require(not state.exists(), "El directorio de evidencia ya existe; no se sobrescribe")
    venv = ROOT / ".venv-historical"
    if args.reuse_environment:
        require((venv / "Scripts/python.exe").is_file(), "No existe el entorno que se pidio reutilizar")
    else:
        require(not venv.exists(), "El entorno .venv-historical ya existe; usar --reuse-environment para verificarlo y reutilizarlo")
    require(1 <= args.local_port <= 65535 and 1 <= args.docker_port <= 65535, "Puertos fuera de rango")
    port_available(args.local_port)
    if not args.skip_docker:
        require(args.local_port != args.docker_port, "Los puertos de Windows y Docker deben ser diferentes")
        port_available(args.docker_port)
        require(shutil.which("docker") is not None, "Docker no esta en PATH; abrir Docker Desktop")
    state.mkdir(parents=True)
    summary = {"candidate_base": "60c8764a2e2840503a598bf0c6605f1e2e1a6baf",
               "fixture_only": True, "historical_fixture_only": True,
               "original_pmum_artifact_loaded": False, "configuration_calibrated": False,
               "python_base": sys.version,
               "started_utc": datetime.now(timezone.utc).isoformat()}

    def command(arguments, label, cwd=ROOT, custom_env=None):
        print("ETAPA: " + label, flush=True)
        result = subprocess.run([str(x) for x in arguments], cwd=cwd, env=custom_env or env,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        filename = "".join(c if c.isalnum() or c in "_-" else "_" for c in label) + ".log"
        (state / filename).write_text(result.stdout + "\nSTDERR:\n" + result.stderr, encoding="utf-8")
        if result.returncode:
            print((result.stdout + result.stderr)[-8000:], flush=True)
            raise RuntimeError("Fallo la etapa " + label + "; revisar " + str(state / filename))
        if label.startswith("suite"):
            print(result.stderr[-1200:], flush=True)
        summary[label] = "PASS"
        return result.stdout.strip()

    container_id = None
    process = None
    logs = []
    try:
        summary["tested_commit"] = command(["git", "rev-parse", "HEAD"], "git_tested_commit")
        summary["tested_branch"] = command(["git", "branch", "--show-current"], "git_tested_branch")
        tracked = command(["git", "ls-files", "-z"], "git_tracked_files").split("\0")
        untracked = command(["git", "ls-files", "--others", "--exclude-standard", "-z"],
                            "git_untracked_files").split("\0")
        source_manifest = {}
        for name in sorted(set(tracked + untracked) - {""}):
            source = ROOT / name
            if source.is_file():
                source_manifest[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        encoded_manifest = json.dumps(source_manifest, sort_keys=True).encode("utf-8")
        summary["tested_source_manifest_sha256"] = hashlib.sha256(encoded_manifest).hexdigest()
        (state / "tested_source_manifest.json").write_text(
            json.dumps(source_manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if not args.skip_docker:
            require(command(["docker", "info", "--format", "{{.OSType}}"], "docker_info") == "linux",
                    "Docker debe estar en modo Linux")
        python = venv / "Scripts" / "python.exe"
        if not args.reuse_environment:
            command([sys.executable, "-m", "venv", venv], "crear_entorno")
            command([python, "-m", "pip", "install", "-r", "requirements-integration-tools.txt"], "instalar_dependencias")
        # Reutilizar no permite omitir controles ni instalar versiones diferentes.
        probe = command([python, "-c",
                         "import sys,json,importlib.metadata as m; "
                         "print(json.dumps({'python':list(sys.version_info[:2]),"
                         "'versions':{n:m.version(n) for n in json.loads(sys.argv[1])}}))",
                         json.dumps(pinned_requirements(ROOT / "requirements-integration-tools.txt"))],
                        "verificar_entorno")
        installed = json.loads(probe)
        require(installed["python"] == [3, 10], "El entorno separado no usa Python 3.10")
        for name, version in pinned_requirements(ROOT / "requirements-integration-tools.txt").items():
            require(installed["versions"].get(name) == version, "Version incompatible del entorno: " + name)
        summary["environment_reused"] = args.reuse_environment
        command([python, "-m", "pip", "check"], "pip_check")
        command([python, "-m", "unittest", "discover", "-s", "tests", "-t", "."], "suite_tests")
        command([python, "-m", "unittest", "test_child_choice_signals", "test_intervention_history_reader"],
                "suite_raiz_unittest")
        legacy = state / "legacy-smoke"
        (legacy / "models").mkdir(parents=True)
        shutil.copyfile(ROOT / "models/pmu_linear_v1.joblib", legacy / "models/pmu_linear_v1.joblib")
        for name in ("test_inference.py", "test_intervention_engine.py", "test_intervention_history.py",
                     "test_intervention_service.py", "test_recommendations.py", "test_weekly_analysis.py"):
            output = command([python, ROOT / name], "legacy_" + name, cwd=legacy)
            require("ERROR" not in output, "El script heredado imprimio ERROR; revisar su log")
        profile = state / "smoke-only-profile.json"
        shutil.copyfile(ROOT / "tests/fixtures/historical_c1_smoke_only.json", profile)
        env.update({"ANALYTICS_SERVICE_TOKEN": secrets.token_hex(32),
                    "ANALYTICS_PMUM_ENABLED": "false", "ANALYTICS_ACTIVITIES_ENABLED": "true",
                    "ANALYTICS_HISTORICAL_ENABLED": "true", "ANALYTICS_HOST": "127.0.0.1",
                    "ANALYTICS_PORT": str(args.local_port), "ANALYTICS_HISTORICAL_CONFIG_PATH": str(profile),
                    "ANALYTICS_HISTORICAL_REPOSITORY_PATH": str(state / "windows-state/history.json")})
        base = "http://127.0.0.1:" + str(args.local_port)

        def start_server(suffix):
            stdout = (state / ("server-" + suffix + ".stdout.log")).open("w", encoding="utf-8")
            stderr = (state / ("server-" + suffix + ".stderr.log")).open("w", encoding="utf-8")
            logs.extend((stdout, stderr))
            child = subprocess.Popen([str(python), "analytics_api.py"], cwd=ROOT, env=env,
                                     stdout=stdout, stderr=stderr)
            try:
                wait_http(child, base)
            except BaseException:
                child.kill()
                child.wait(timeout=10)
                raise
            return child

        smoke_script = ROOT / "tools/validation/smoke_analytics_historical.py"
        receipt = state / "windows-http-results.json"
        process = start_server("first")
        command([python, smoke_script, "--phase", "seed", "--base-url", base, "--receipt-file", receipt],
                "windows_http_seed")
        # Terminar solo el proceso creado aqui, para comprobar recuperacion tras corte.
        process.kill()
        process.wait(timeout=10)
        process = None
        process = start_server("restart")
        command([python, smoke_script, "--phase", "replay", "--base-url", base, "--receipt-file", receipt],
                "windows_http_restart_replay")
        process.terminate()
        process.wait(timeout=10)
        process = None

        audit_script = ROOT / "tools/validation/audit_c1_repository.py"
        command([python, audit_script, "--repository", state / "windows-state/history.json",
                 "--config", profile, "--output", state / "windows-c1-snapshot-audit.json"],
                "windows_c1_snapshot_audit")
        model_dir = args.model_dir
        expected_model = model_dir / "hu_pmum_sf_experimental_v1.joblib"
        expected_manifest = model_dir / "hu_pmum_sf_experimental_v1.json"
        if expected_model.exists() or expected_manifest.exists():
            require(expected_model.is_file() and expected_manifest.is_file(), "Entrega HU v1 incompleta")
            command([python, ROOT / "tools/validation/verify_pmum_artifact_v1.py", "--model-dir", model_dir,
                     "--output", state / "pmum-original-artifact-audit.json"], "pmum_original_artifact")
            summary["original_pmum_artifact_loaded"] = True
            summary["fixture_only"] = False
            env.update({"ANALYTICS_PMUM_ENABLED": "true", "ANALYTICS_MODEL_PATH": str(expected_model),
                        "ANALYTICS_MODEL_MANIFEST_PATH": str(expected_manifest),
                        "ANALYTICS_MODEL_SHA256": "56c991f40e56d2241196dc6f9efc1c9027c079e98a1b67549f48b10292e371e0"})
            process = start_server("pmum-c1-coexistence")
            command([python, ROOT / "tools/validation/smoke_pmum_c1.py", "--base-url", base,
                     "--output", state / "pmum-c1-http.json"], "windows_pmum_c1_http")
            command([python, smoke_script, "--phase", "replay", "--base-url", base, "--receipt-file", receipt],
                    "windows_c1_replay_with_pmum")
            process.terminate()
            process.wait(timeout=10)
            process = None
            env["ANALYTICS_PMUM_ENABLED"] = "false"
        else:
            summary["pmum_original_artifact"] = "PENDING: originales HU v1 no disponibles en model-dir"
            summary["windows_pmum_c1_http"] = "PENDING: requiere originales HU v1"
            print("PENDIENTE: no se encontro HU v1 original; las pruebas ficticias no lo sustituyen", flush=True)

        if not args.skip_docker:
            compose_env = {**env, "ANALYTICS_HISTORICAL_CONFIG_FILE": str(profile)}
            command(["docker", "compose", "-f", "compose.analytics-historical.candidate.yml", "config", "--quiet"],
                    "compose_config", custom_env=compose_env)
            image = "modera-analytics:historical-candidate-" + run_id
            volume = "modera-historical-smoke-" + run_id
            command(["docker", "build", "-f", "Dockerfile.analytics", "-t", image, "."], "docker_build")
            command(["docker", "volume", "create", "--label", "modera.purpose=historical-smoke", volume],
                    "docker_volume")
            summary["docker_volume_retained"] = volume
            docker_env = {**env, "ANALYTICS_HOST": "0.0.0.0", "ANALYTICS_PORT": "8765",
                          "ANALYTICS_HISTORICAL_CONFIG_PATH": "/config/historical.json",
                          "ANALYTICS_HISTORICAL_REPOSITORY_PATH": "/var/lib/modera/historical/history.json"}
            argv = ["docker", "run", "-d", "--name", "modera-historical-smoke-" + run_id,
                    "--read-only", "--tmpfs", "/tmp", "-p", "127.0.0.1:" + str(args.docker_port) + ":8765",
                    "--mount", "type=volume,source=" + volume + ",target=/var/lib/modera/historical",
                    "--mount", "type=bind,source=" + str(profile) + ",target=/config/historical.json,readonly"]
            for key in ("ANALYTICS_SERVICE_TOKEN", "ANALYTICS_PMUM_ENABLED", "ANALYTICS_ACTIVITIES_ENABLED",
                        "ANALYTICS_HISTORICAL_ENABLED", "ANALYTICS_HOST", "ANALYTICS_PORT",
                        "ANALYTICS_HISTORICAL_CONFIG_PATH", "ANALYTICS_HISTORICAL_REPOSITORY_PATH"):
                argv.extend(("--env", key))
            argv.append(image)
            container_id = command(argv, "docker_start", custom_env=docker_env).strip()
            docker_base = "http://127.0.0.1:" + str(args.docker_port)
            wait_http(None, docker_base, timeout=30)
            docker_receipt = state / "docker-http-results.json"
            command([python, smoke_script, "--phase", "seed", "--base-url", docker_base,
                     "--receipt-file", docker_receipt], "docker_http_seed")
            command(["docker", "restart", container_id], "docker_restart")
            wait_http(None, docker_base, timeout=30)
            command([python, smoke_script, "--phase", "replay", "--base-url", docker_base,
                     "--receipt-file", docker_receipt], "docker_http_restart_replay")
            identity = command(["docker", "exec", container_id, "id"], "docker_identity")
            require("uid=10001" in identity and "gid=10001" in identity, "Usuario Docker inesperado")
            deadline = time.monotonic() + 60
            while True:
                health = command(["docker", "inspect", "--format", "{{.State.Health.Status}}", container_id],
                                 "docker_healthcheck")
                if health == "healthy":
                    break
                require(health != "unhealthy" and time.monotonic() < deadline,
                        "El healthcheck Docker no quedo healthy; revisar logs")
                time.sleep(2)
            summary["docker_image_id"] = command(["docker", "image", "inspect", image, "--format", "{{.Id}}"],
                                                 "docker_image_identity")
            command(["docker", "logs", "--tail", "100", container_id], "docker_logs")
            snapshot = state / "docker-history-snapshot.json"
            command(["docker", "cp", container_id + ":/var/lib/modera/historical/history.json", snapshot],
                    "docker_c1_snapshot_copy")
            command([python, audit_script, "--repository", snapshot, "--config", profile,
                     "--output", state / "docker-c1-snapshot-audit.json"], "docker_c1_snapshot_audit")
            if summary["original_pmum_artifact_loaded"]:
                # Sólo se reemplaza el contenedor creado en esta ejecución; se
                # conserva su volumen y se montan ambos originales en sólo lectura.
                command(["docker", "stop", container_id], "docker_fixture_stop")
                command(["docker", "rm", container_id], "docker_fixture_remove")
                container_id = None
                pmum_argv = list(argv[:-1])
                pmum_argv[pmum_argv.index("--name") + 1] += "-pmum"
                for source, target in ((expected_model, "/models/hu.joblib"),
                                       (expected_manifest, "/models/hu.json")):
                    pmum_argv.extend(("--mount", "type=bind,source=" + str(source.resolve())
                                      + ",target=" + target + ",readonly"))
                pmum_env = {**docker_env, "ANALYTICS_PMUM_ENABLED": "true",
                            "ANALYTICS_MODEL_PATH": "/models/hu.joblib",
                            "ANALYTICS_MODEL_MANIFEST_PATH": "/models/hu.json",
                            "ANALYTICS_MODEL_SHA256": "56c991f40e56d2241196dc6f9efc1c9027c079e98a1b67549f48b10292e371e0"}
                for key in ("ANALYTICS_MODEL_PATH", "ANALYTICS_MODEL_MANIFEST_PATH", "ANALYTICS_MODEL_SHA256"):
                    pmum_argv.extend(("--env", key))
                pmum_argv.append(image)
                container_id = command(pmum_argv, "docker_pmum_start", custom_env=pmum_env)
                wait_http(None, docker_base, timeout=30)
                command([python, ROOT / "tools/validation/smoke_pmum_c1.py", "--base-url", docker_base,
                         "--output", state / "docker-pmum-c1-http.json"], "docker_pmum_c1_http")
                command([python, smoke_script, "--phase", "replay", "--base-url", docker_base,
                         "--receipt-file", docker_receipt], "docker_c1_replay_with_pmum")
                pmum_snapshot = state / "docker-history-with-pmum.json"
                command(["docker", "cp", container_id + ":/var/lib/modera/historical/history.json", pmum_snapshot],
                        "docker_c1_snapshot_with_pmum")
                require(pmum_snapshot.read_bytes() == snapshot.read_bytes(),
                        "El replay con PMUM altero los bytes del historico")
                summary["docker_history_bytes_unchanged_with_pmum"] = True
            else:
                summary["docker_pmum_c1_http"] = "PENDING: requiere originales HU v1"
        else:
            summary["docker"] = "PENDING: skipped explicitly"
        command(["git", "diff", "--check"], "git_diff_check")
        pending = [key for key, value in summary.items()
                   if isinstance(value, str) and value.startswith("PENDING:")]
        summary["pending_evidence"] = pending
        summary["status"] = "PASS_WITH_PENDING_EVIDENCE" if pending else "PASS"
        print(summary["status"] + ": etapas ejecutadas aprobadas; historico ficticio y no calibrado", flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        summary["status"] = "FAILED"
        summary["error"] = str(exc)
        print("ERROR: " + str(exc), file=sys.stderr)
        if container_id:
            try:
                command(["docker", "logs", "--tail", "100", container_id], "docker_failure_logs")
            except (OSError, RuntimeError):
                pass
        return 1
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        for stream in logs:
            stream.close()
        if container_id:
            # Elimina solo el contenedor de esta ejecución; conserva su volumen de prueba.
            subprocess.run(["docker", "rm", "-f", container_id], env=env, capture_output=True)
        summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (state / "validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print("EVIDENCIA: " + str(state), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-docker", action="store_true")
    parser.add_argument("--reuse-environment", action="store_true",
                        help="Verifica y reutiliza .venv-historical; conserva las evidencias anteriores")
    parser.add_argument("--local-port", type=int, default=8767)
    parser.add_argument("--docker-port", type=int, default=8768)
    parser.add_argument("--state-root", type=Path)
    parser.add_argument("--model-dir", type=Path,
                        default=Path.home() / "Documents/modera_pmum_experimental",
                        help="Originales HU v1 registrados; nunca los entrena ni sobrescribe")
    args = parser.parse_args()
    try:
        return run(args)
    except (OSError, RuntimeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
