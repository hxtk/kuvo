# LICENSE HEADER MANAGED BY add-license-header
#
# Kuvo: reproducible OCI images for Python projects
# Copyright (C) 2026  Peter Sanders
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import hashlib
import itertools
import json
from typing import TYPE_CHECKING
from typing import Literal

import pydantic
from oras import client
from oras import container

from kuvo.oci import models

if TYPE_CHECKING:
    import pathlib

_INDEX_MEDIA_TYPE = "application/vnd.oci.image.index.v1+json"
_IMAGE_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
_TAR_MEDIA_TYPE = "application/vnd.oci.image.layer.v1.tar"


class NoMatchingManifestError(Exception):
    """Indicates an Image Index had no manifest matching a particular platform."""

    def __init__(self, desc: models.ImageIndex, os: str, arch: str) -> None:
        """Indicates no suitable manifest for a requested platform."""
        self.descriptor = desc
        self.os = os
        self.arch = arch
        super().__init__(f"No manifest matched os={os}, arch={arch}.")


def pull(
    oci: pathlib.Path,
    ref: str,
    arch: str = "amd64",
    os: str = "linux",
    insecure: bool = False,
) -> None:
    """Fetch an OCI layout directory of an image reference."""
    con = container.Container(ref)
    c = client.OrasClient(insecure=insecure)
    idx = models.ImageIndex.model_validate(
        c.get_manifest(con, allowed_media_type=[_INDEX_MEDIA_TYPE])
    )

    for m in idx.manifests:
        if m.media_type != _IMAGE_MEDIA_TYPE or not m.platform:
            continue
        if m.platform.architecture != arch or m.platform.os != os:
            continue
        mfd = m
        break
    else:
        raise NoMatchingManifestError(idx, arch=arch, os=os)

    blobs = oci / "blobs/sha256"
    blobs.mkdir(exist_ok=True, parents=True)

    mfcon = container.Container(ref)
    mfcon.digest = mfd.digest
    mf = models.ImageManifest.model_validate(
        c.get_manifest(mfcon),
    )
    mf_data = mf.model_dump_json(exclude_none=True).encode()
    mf_digest = hashlib.sha256(mf_data).hexdigest()
    (blobs / mf_digest).write_bytes(mf_data)

    (oci / "oci-layout").write_text(json.dumps({"imageLayoutVersion": "1.0.0"}))
    blobs.mkdir(exist_ok=True, parents=True)
    for layer in mf.layers:
        _fetch_descriptor(c, con, blobs, layer)
    _fetch_descriptor(c, con, blobs, mf.config)

    mfd.digest = f"sha256:{mf_digest}"
    mfd.size = len(mf_data)
    (oci / "index.json").write_text(
        models.ImageIndex(
            media_type=_INDEX_MEDIA_TYPE,
            manifests=[mfd],
            annotations=idx.annotations,
        ).model_dump_json(exclude_none=True)
    )


def _fetch_descriptor(
    c: client.OrasClient,
    con: container.Container,
    outdir: pathlib.Path,
    desc: models.Descriptor,
) -> pathlib.Path:
    digest = desc.digest
    outfile = outdir / digest.replace("sha256:", "")
    c.download_blob(
        con,
        digest=digest,
        outfile=outfile,
    )
    return outfile


def add_layer(
    oci: pathlib.Path,
    tar: pathlib.Path,
    arch: str | None = None,
    os: str | None = None,
) -> None:
    """Add a layer to an image manifest, replacing the original manifest."""
    size = tar.stat().st_size
    with tar.open("rb") as f:
        digest = hashlib.file_digest(f, hashlib.sha256).hexdigest()
    tar.copy(oci / f"blobs/sha256/{digest}")

    desc = models.Descriptor(
        size=size, mediaType=_TAR_MEDIA_TYPE, digest=f"sha256:{digest}"
    )
    idxf = oci / "index.json"
    idx = models.ImageIndex.model_validate_json(idxf.read_text())
    for manifest in idx.manifests:
        if (
            arch
            and manifest.platform
            and manifest.platform.architecture != arch
        ):
            continue
        if os and manifest.platform and manifest.platform.os != os:
            continue

        manifest.digest, manifest.size = _add_manifest_layer(
            oci,
            manifest,
            desc,
        )

    idxf.write_text(idx.model_dump_json(exclude_none=True))


def _add_manifest_layer(
    oci: pathlib.Path,
    manifest: models.Descriptor,
    layer: models.Descriptor,
) -> tuple[str, int]:
    mfp = oci / f"blobs/{manifest.digest.replace(':', '/')}"
    mf = models.ImageManifest.model_validate_json(mfp.read_text())
    mf.layers.append(layer)

    mf.config.digest, mf.config.size = _add_config_layer(oci, mf.config, layer)

    data = mf.model_dump_json(exclude_none=True).encode()
    digest = hashlib.sha256(data).hexdigest()
    mfp.write_bytes(data)
    mfp.rename(oci / f"blobs/sha256/{digest}")

    return f"sha256:{digest}", len(data)


def _add_config_layer(
    oci: pathlib.Path,
    config: models.Descriptor,
    layer: models.Descriptor,
) -> tuple[str, int]:
    cfp = oci / f"blobs/{config.digest.replace(':', '/')}"
    cf = models.ImageConfig.model_validate_json(cfp.read_text())
    cf.rootfs.diff_ids.append(layer.digest)

    data = cf.model_dump_json(exclude_none=True).encode()
    digest = hashlib.sha256(data).hexdigest()

    cfp.write_bytes(data)
    cfp.rename(oci / f"blobs/sha256/{digest}")

    return f"sha256:{digest}", len(data)


def ensure_config(
    oci: pathlib.Path,
    paths: list[str],
    entrypoint: list[str] | None = None,
    cmd: list[str] | None = None,
) -> None:
    """Ensure the runtime configuration for an image has certain properties.

    Attrs:
        paths: a list of paths that should exist in the runtime PATH.
            If any paths don't already exist in PATH, all get prepended
            to the PATH environment variable.
        entrypoint: a list of arguments serving as the command entrypoint.
            Preserves the original entrypoint if None.
        cmd: a list of arguments serving as the command. Preserves the original
            command if None.
    """
    idxf = oci / "index.json"
    idx = models.ImageIndex.model_validate_json(idxf.read_text())
    for manifest in idx.manifests:
        manifest.digest, manifest.size = _ensure_manifest_config(
            oci,
            manifest,
            paths,
            entrypoint,
            cmd,
        )

    idxf.write_text(idx.model_dump_json(exclude_none=True))


def _ensure_manifest_config(
    oci: pathlib.Path,
    manifest: models.Descriptor,
    paths: list[str],
    entrypoint: list[str] | None = None,
    cmd: list[str] | None = None,
) -> tuple[str, int]:
    mfp = oci / f"blobs/{manifest.digest.replace(':', '/')}"
    mf = models.ImageManifest.model_validate_json(mfp.read_text())

    mf.config.digest, mf.config.size = _ensure_config_config(
        oci,
        mf.config,
        paths,
        entrypoint,
        cmd,
    )

    data = mf.model_dump_json(exclude_none=True).encode()
    digest = hashlib.sha256(data).hexdigest()
    mfp.write_bytes(data)
    mfp.rename(oci / f"blobs/sha256/{digest}")

    return f"sha256:{digest}", len(data)


def _ensure_config_config(
    oci: pathlib.Path,
    config: models.Descriptor,
    paths: list[str],
    entrypoint: list[str] | None = None,
    cmd: list[str] | None = None,
) -> tuple[str, int]:
    cfp = oci / f"blobs/{config.digest.replace(':', '/')}"
    cf = models.ImageConfig.model_validate_json(cfp.read_text())
    if not cf.config:
        cf.config = models.RuntimeConfig(Env=[f"PATH={':'.join(paths)}"])
    elif not cf.config.env:
        cf.config.env = [f"PATH={':'.join(paths)}"]

    else:
        for idx, var in enumerate(cf.config.env):
            if not var.startswith("PATH="):
                continue
            ex_paths = var.removeprefix("PATH=").split(":")
            if not all(x in ex_paths for x in paths):
                paths = [*paths, *ex_paths]
                cf.config.env[idx] = f"PATH={':'.join(paths)}"
            break
        else:
            cf.config.env.append(f"PATH={':'.join(paths)}")

    if entrypoint is not None:
        cf.config.entry = entrypoint
    if cmd is not None:
        cf.config.cmd = cmd

    data = cf.model_dump_json(exclude_none=True).encode()
    digest = hashlib.sha256(data).hexdigest()

    cfp.write_bytes(data)
    cfp.rename(oci / f"blobs/sha256/{digest}")

    return f"sha256:{digest}", len(data)


def tag(oci: pathlib.Path, repositories: list[str], tags: list[str]) -> None:
    """Apply the specified tags to all OCI image manifests in an index."""
    idxf = oci / "index.json"
    idx = models.ImageIndex.model_validate_json(idxf.read_text())
    manifests = []
    for repository, tag, mf in itertools.product(
        repositories, tags, idx.manifests
    ):
        mf = mf.model_copy()
        if mf.annotations is None:
            mf.annotations = {}
        mf.annotations["org.opencontainers.image.ref.name"] = (
            f"{repository}:{tag}"
        )
        manifests.append(mf)

    idx.manifests = manifests
    idxf.write_text(idx.model_dump_json(exclude_none=True))
