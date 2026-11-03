"""License guard: only CC-BY-4.0 approved sources allowed."""
import csv
import datetime
import os
import re
import sys
from pathlib import Path

ALLOWED_LICENSES = {"CC-BY-4.0"}
SYNTHETIC = "repo-generated"

MANIFEST_COLUMNS = [
    "source_id",
    "doi",
    "citation",
    "expected_license",
    "pdf_url",
    "supplement_url",
    "status",
    "license_verified_at",
]

FORBIDDEN_TERMS = [
    "muse-image",
    "images/generations",
    "images/edits",
    "generate_image",
    "edit_image",
    "inpaint",
    "img2img",
    "diffusers",
    "sam-3",
    "meta_sam_parser",
    "meta-sam-parser",
    "segment-anything",
]

class LicenseFlag(SystemExit):
    pass

def _repo_root():
    return Path(__file__).resolve().parent.parent

def _manifest_path():
    v = os.environ.get("PAPER_MANIFEST_PATH")
    if v:
        return Path(v)
    return _repo_root() / "data" / "paper_manifest.csv"

def _flags_path():
    v = os.environ.get("LICENSE_FLAGS_PATH")
    if v:
        return Path(v)
    return _repo_root() / "LICENSE_FLAGS.md"

def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def flag(reason, where="check"):
    p = _flags_path()
    try:
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# License flags\n", encoding="utf-8")
        with p.open("a", encoding="utf-8") as f:
            f.write(f"- {_utc_now()} | {where} | {reason}\n")
    except Exception:
        pass
    print(f"LICENSE FLAG - STOPPED: {reason}", file=sys.stderr)
    raise LicenseFlag(2)

def load_manifest():
    p = _manifest_path()
    if not p.exists():
        flag(f"manifest missing: {p}", "manifest")
    try:
        with p.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != MANIFEST_COLUMNS:
                flag(f"manifest columns must be exactly {MANIFEST_COLUMNS}, got {reader.fieldnames}", "manifest")
            out = {}
            for row in reader:
                out[row.get("source_id", "")] = row
            return out
    except LicenseFlag:
        raise
    except Exception as e:
        flag(f"cannot read manifest: {e}", "manifest")

def source_ok(source_id):
    try:
        m = load_manifest()
    except LicenseFlag:
        return False
    row = m.get(source_id)
    if row is None:
        return False
    if row.get("status") != "approved":
        return False
    if row.get("expected_license") not in ALLOWED_LICENSES:
        return False
    if not (row.get("license_verified_at") or "").strip():
        return False
    return True

def assert_sendable(source_id, what):
    if source_id == SYNTHETIC:
        return
    if source_ok(source_id):
        return
    flag(f"not sendable: {source_id} for {what}", source_id)

def _parse_req_name(line):
    line = line.split("#", 1)[0].strip()
    if not line:
        return None
    if line.startswith("-") or "://" in line:
        return None
    m = re.match(r"^([A-Za-z0-9_.\-]+)", line)
    if not m:
        return None
    return m.group(1).lower().replace("_", "-")

def check(root=None):
    problems = []
    r = Path(root) if root is not None else _repo_root()
    mp = Path(os.environ.get("PAPER_MANIFEST_PATH", str(r / "data" / "paper_manifest.csv")))
    try:
        with mp.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != MANIFEST_COLUMNS:
                problems.append(f"manifest: bad columns {reader.fieldnames}")
                rows = []
            else:
                rows = list(reader)
    except FileNotFoundError:
        return [f"manifest missing: {mp}"]
    manifest_by_id = {row.get("source_id", ""): row for row in rows}
    approved_ids = {sid for sid, row in manifest_by_id.items() if row.get("status") == "approved" and row.get("expected_license") in ALLOWED_LICENSES}
    for row in rows:
        sid = row.get("source_id", "")
        st = row.get("status", "")
        if st not in ("approved", "excluded"):
            problems.append(f"manifest {sid}: bad status {st}")
            continue
        if st == "approved":
            if row.get("expected_license") not in ALLOWED_LICENSES:
                problems.append(f"manifest {sid}: approved but license not allowed")
            if not (row.get("doi") or "").strip():
                problems.append(f"manifest {sid}: approved but doi empty")
            if not (row.get("pdf_url") or "").strip():
                problems.append(f"manifest {sid}: approved but pdf_url empty")
        else:
            if (row.get("pdf_url") or "").strip():
                problems.append(f"manifest {sid}: excluded but pdf_url not empty")
    data_dir = r / "data"
    if data_dir.exists():
        for jp in data_dir.rglob("*.json"):
            try:
                import json as _json
                d = _json.loads(jp.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(d, dict) or "source_id" not in d:
                continue
            sid = d.get("source_id")
            lic = d.get("license")
            if sid != SYNTHETIC and sid not in approved_ids:
                problems.append(f"{jp}: source_id {sid} not approved")
            if lic not in ALLOWED_LICENSES and lic != SYNTHETIC:
                problems.append(f"{jp}: bad license {lic}")
            is_synth = (sid == SYNTHETIC or lic == SYNTHETIC)
            if not is_synth:
                if not (d.get("doi") or ""):
                    problems.append(f"{jp}: missing doi")
                if not (d.get("attribution") or ""):
                    problems.append(f"{jp}: missing attribution")
            if d.get("ai_generated") is True:
                problems.append(f"{jp}: ai_generated true")
    for base in [r / "data", r / "readable_20pct_test_vault"]:
        if not base.exists():
            continue
        for cp in base.rglob("*.csv"):
            try:
                with cp.open("r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames is None or "license" not in reader.fieldnames:
                        continue
                    has_sid = "source_id" in reader.fieldnames
                    for i, row in enumerate(reader, start=2):
                        lic = (row.get("license") or "").strip()
                        if lic not in ALLOWED_LICENSES and lic != SYNTHETIC:
                            problems.append(f"{cp}:{i}: bad license '{lic}'")
                            break
                        if has_sid:
                            sid = (row.get("source_id") or "").strip()
                            if sid and sid != SYNTHETIC and sid not in approved_ids:
                                problems.append(f"{cp}:{i}: bad source_id '{sid}'")
                                break
            except Exception:
                continue
    allowed_pkgs = set()
    ap = r / "config" / "allowed_packages.txt"
    if ap.exists():
        for line in ap.read_text(encoding="utf-8").splitlines():
            s = line.strip().lower()
            if s:
                allowed_pkgs.add(s.replace("_", "-"))
    for rp in r.glob("requirements*.txt"):
        try:
            for line in rp.read_text(encoding="utf-8").splitlines():
                n = _parse_req_name(line)
                if n is None:
                    continue
                if n not in allowed_pkgs:
                    problems.append(f"{rp.name}: package {n} not in allowed_packages.txt")
        except Exception:
            continue
    scan_files = []
    for dname in ["src", "scripts"]:
        d = r / dname
        if d.exists():
            scan_files.extend(d.rglob("*.py"))
    app_py = r / "app.py"
    if app_py.exists():
        scan_files.append(app_py)
    allowed_meta = {"src/meta_gateway.py","src/extract.py","src/digitise.py","src/micrograph.py"}
    for fp in scan_files:
        try:
            rel = fp.relative_to(r).as_posix()
        except Exception:
            continue
        if rel == "src/license_guard.py":
            continue
        try:
            txt = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "api.meta.ai" in txt and rel != "src/meta_gateway.py":
            problems.append(f"{rel}: api.meta.ai only allowed in src/meta_gateway.py")
        if "meta_gateway" in txt:
            is_scripts = rel.startswith("scripts/")
            if rel not in allowed_meta and not is_scripts:
                problems.append(f"{rel}: meta_gateway import not allowed here")
        low = txt.lower()
        for term in FORBIDDEN_TERMS:
            if term.lower() in low:
                problems.append(f"{rel}: forbidden term {term}")
                break
    return problems

def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] != "check":
        print("usage: python -m src.license_guard check")
        return 1
    problems = check()
    if problems:
        for p in problems:
            print(p)
        fp = _flags_path()
        try:
            if not fp.exists():
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text("# License flags\n", encoding="utf-8")
            with fp.open("a", encoding="utf-8") as f:
                for p in problems:
                    f.write(f"- {_utc_now()} | check | {p}\n")
        except Exception:
            pass
        print("LICENSE FLAG - STOPPED", file=sys.stderr)
        return 2
    print("license check passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
