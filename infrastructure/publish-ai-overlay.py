"""Publish changed AI application files as an OCI layer without Docker.

This reuses the currently deployed Lambda image layers and appends a small,
auditable /var/task overlay. It is intended for development machines where a
Docker daemon is unavailable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = ROOT / "Member3_AI_Backend_" / "Member3_AI_Backend"
FILES = {
    AI_ROOT / "api" / "main.py": "var/task/api/main.py",
    AI_ROOT / "api" / "priority_policy.py": "var/task/api/priority_policy.py",
    AI_ROOT / "models" / "final" / "category_model.joblib":
        "var/task/models/final/category_model.joblib",
    AI_ROOT / "models" / "final" / "priority_model.joblib":
        "var/task/models/final/priority_model.joblib",
    AI_ROOT / "models" / "final" / "model_metadata.json":
        "var/task/models/final/model_metadata.json",
}


def aws(profile: str, region: str, *args: str) -> str:
    command = ["aws", *args, "--profile", profile, "--region", region]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_layer() -> tuple[bytes, bytes]:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for source, target in FILES.items():
            data = source.read_bytes()
            info = tarfile.TarInfo(target)
            info.size = len(data)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    uncompressed = stream.getvalue()
    return uncompressed, gzip.compress(uncompressed, compresslevel=9, mtime=0)


def upload_blob(
    profile: str,
    region: str,
    repository: str,
    path: Path,
    digest: str,
) -> None:
    initiated = json.loads(aws(
        profile, region, "ecr", "initiate-layer-upload",
        "--repository-name", repository, "--output", "json",
    ))
    upload_id = initiated["uploadId"]
    size = path.stat().st_size
    aws(
        profile, region, "ecr", "upload-layer-part",
        "--repository-name", repository,
        "--upload-id", upload_id,
        "--part-first-byte", "0",
        "--part-last-byte", str(size - 1),
        "--layer-part-blob", f"fileb://{path}",
        "--output", "json",
    )
    aws(
        profile, region, "ecr", "complete-layer-upload",
        "--repository-name", repository,
        "--upload-id", upload_id,
        "--layer-digests", f"sha256:{digest}",
        "--output", "json",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="dcs-assignment")
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--repository", default="dcs-ticket-system-ai")
    parser.add_argument("--base-tag", required=True)
    parser.add_argument("--new-tag", required=True)
    args = parser.parse_args()

    missing = [str(path) for path in FILES if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing AI overlay files: {missing}")

    response = json.loads(aws(
        args.profile, args.region, "ecr", "batch-get-image",
        "--repository-name", args.repository,
        "--image-ids", f"imageTag={args.base_tag}",
        "--accepted-media-types", "application/vnd.oci.image.manifest.v1+json",
        "--output", "json",
    ))
    manifest = json.loads(response["images"][0]["imageManifest"])
    config_digest = manifest["config"]["digest"]
    download = json.loads(aws(
        args.profile, args.region, "ecr", "get-download-url-for-layer",
        "--repository-name", args.repository,
        "--layer-digest", config_digest,
        "--output", "json",
    ))
    with urllib.request.urlopen(download["downloadUrl"]) as response_stream:
        config = json.loads(response_stream.read())

    tar_bytes, layer_bytes = make_layer()
    layer_digest = sha256(layer_bytes)
    config["rootfs"]["diff_ids"].append(f"sha256:{sha256(tar_bytes)}")
    config.setdefault("history", []).append({
        "created": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "created_by": "Codex teammate AI v2.0.0 overlay",
    })
    config_bytes = json.dumps(config, separators=(",", ":")).encode()
    new_config_digest = sha256(config_bytes)

    output_dir = ROOT / ".tmp" / "ai-oci-overlay"
    output_dir.mkdir(parents=True, exist_ok=True)
    layer_path = output_dir / "layer.tar.gz"
    config_path = output_dir / "config.json"
    layer_path.write_bytes(layer_bytes)
    config_path.write_bytes(config_bytes)

    upload_blob(args.profile, args.region, args.repository, layer_path, layer_digest)
    upload_blob(args.profile, args.region, args.repository, config_path, new_config_digest)

    manifest["config"] = {
        "mediaType": "application/vnd.oci.image.config.v1+json",
        "digest": f"sha256:{new_config_digest}",
        "size": len(config_bytes),
    }
    manifest["layers"].append({
        "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        "digest": f"sha256:{layer_digest}",
        "size": len(layer_bytes),
    })
    manifest_text = json.dumps(manifest, separators=(",", ":"))
    result = json.loads(aws(
        args.profile, args.region, "ecr", "put-image",
        "--repository-name", args.repository,
        "--image-tag", args.new_tag,
        "--image-manifest", manifest_text,
        "--image-manifest-media-type", "application/vnd.oci.image.manifest.v1+json",
        "--output", "json",
    ))
    print(json.dumps({
        "image_tag": args.new_tag,
        "image_digest": result["image"]["imageId"]["imageDigest"],
        "overlay_size_bytes": len(layer_bytes),
        "files": list(FILES.values()),
    }, indent=2))


if __name__ == "__main__":
    main()
