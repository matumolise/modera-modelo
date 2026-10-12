"""Aplica una entrega verificada en un worktree nuevo, sin commit/push/merge.

La especificación se suministra desde el aplicador de entrega de confianza.
Los tests utilizan repositorios temporales; no requieren red ni Windows.
"""

from dataclasses import dataclass
from hashlib import sha256, sha1
from pathlib import Path, PurePosixPath
import subprocess
import tempfile


@dataclass(frozen=True)
class DeliverySpec:
    base: str
    published_branch: str
    protected_refs: dict
    patch_sha256: str
    changed_blobs: dict


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def git(repo, *arguments):
    result = subprocess.run(
        ["git", "-C", str(repo), *map(str, arguments)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError("Fallo Git: " + arguments[0] + "\n" + result.stderr)
    return result.stdout.strip()


def check_protected(repo, spec):
    for branch, expected in spec.protected_refs.items():
        require(
            git(repo, "rev-parse", "refs/heads/" + branch) == expected,
            "La rama protegida cambio: " + branch,
        )


def check_applied_files(destination, spec):
    for name, expected in spec.changed_blobs.items():
        relative = PurePosixPath(name)
        require(
            not relative.is_absolute() and ".." not in relative.parts,
            "Ruta del inventario invalida",
        )
        path = destination.joinpath(*relative.parts)
        require(path.is_file() and not path.is_symlink(), "Falta archivo aplicado: " + name)
        raw = path.read_bytes()
        blob = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        require(blob == expected, "Archivo aplicado no coincide: " + name)


def prepare_candidate(repo, destination, patch, branch, spec, *, fetch_base=True):
    """fetch_base=False sólo para ensayo offline sobre objetos ya verificados.

    El aplicador de entrega no expone esa excepción: comprueba la base publicada
    mediante fetch antes de crear el worktree. Se conservan los destinos fallidos
    para revisar evidencia; no hay reset/borrado del repositorio original.
    """
    repo, destination, patch = map(lambda p: Path(p).resolve(), (repo, destination, patch))
    require(repo.is_dir(), "Repositorio ausente")
    require(not destination.exists(), "El destino ya existe; no se sobrescribe")
    require(not destination.is_relative_to(repo), "El destino debe estar fuera del repositorio")
    require(branch not in spec.protected_refs, "No usar una rama protegida como destino")
    git(repo, "check-ref-format", "--branch", branch)
    refs = git(repo, "for-each-ref", "--format=%(refname)", "refs/heads/").splitlines()
    require("refs/heads/" + branch not in refs, "La rama destino ya existe")
    raw_patch = patch.read_bytes()
    require(sha256(raw_patch).hexdigest() == spec.patch_sha256, "Huella de parche incompatible")
    origin = git(repo, "remote", "get-url", "origin")
    require(origin in {
        "https://github.com/matumolise/modera-modelo.git",
        "https://github.com/matumolise/modera-modelo",
        "git@github.com:matumolise/modera-modelo.git",
    }, "Origin no corresponde al repositorio revisado")
    original_status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    check_protected(repo, spec)
    if fetch_base:
        git(repo, "fetch", "--no-tags", "origin", spec.published_branch)
        require(git(repo, "rev-parse", "FETCH_HEAD") == spec.base, "La base publicada cambio")
    require(git(repo, "rev-parse", spec.base + "^{commit}") == spec.base, "Base local incompatible")
    try:
        # La configuración temporal sólo afecta esta creación, no el repo original.
        git(repo, "-c", "core.autocrlf=false", "-c", "core.eol=lf",
            "worktree", "add", "-b", branch, destination, spec.base)
        # Git usa exactamente los bytes cuyo hash se comprobó, no relee el original.
        with tempfile.TemporaryDirectory(prefix="modera-verified-patch-") as directory:
            verified_patch = Path(directory) / "candidate.patch"
            verified_patch.write_bytes(raw_patch)
            git(destination, "-c", "core.autocrlf=false", "-c", "core.eol=lf",
                "apply", "--check", verified_patch)
            git(destination, "-c", "core.autocrlf=false", "-c", "core.eol=lf",
                "apply", verified_patch)
        git(destination, "diff", "--check")
        check_applied_files(destination, spec)
    finally:
        check_protected(repo, spec)
        require(
            git(repo, "status", "--porcelain=v1", "--untracked-files=all") == original_status,
            "El estado del repositorio original cambio; conservar evidencia y revisar",
        )
    return {
        "status": "PREPARED_ONLY", "base": spec.base, "branch": branch,
        "destination": str(destination), "patch_sha256": spec.patch_sha256,
        "applied_files_verified": len(spec.changed_blobs),
        "protected_refs_unchanged": True, "original_worktree_status_unchanged": True,
        "commit_created": False, "published": False,
    }
