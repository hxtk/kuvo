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


class InvalidReferenceError(Exception):
    """Indicates a reference that didn't point to an image manifest."""

    def __init__(self, media_type: str) -> None:
        """Indicates the expected and received media types."""
        self.media_type = media_type
        super().__init__(
            f"Expected media type '{_IMAGE_MEDIA_TYPE}'; got '{media_type}'"
        )


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
    mf_data = mf.model_dump_json().encode()
    mf_digest = hashlib.sha256(mf_data).hexdigest()
    (blobs / mf_digest).write_bytes(mf_data)

    (oci / "oci-layout").write_text(json.dumps({"imageLayoutVersion": "1.0.0"}))
    blobs.mkdir(exist_ok=True, parents=True)
    for layer in mf.layers:
        _fetch_descriptor(c, con, blobs, layer)
    _fetch_descriptor(c, con, blobs, mf.config)

    mfd.digest = f"sha256:{mf_digest}"
    (oci / "index.json").write_text(
        models.ImageIndex(
            media_type=_INDEX_MEDIA_TYPE,
            manifests=[mfd],
            annotations=idx.annotations,
        ).model_dump_json()
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
