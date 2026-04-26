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

from typing import Literal

import pydantic


class Platform(pydantic.BaseModel):
    architecture: str
    os: str

    os_version: str | None = pydantic.Field(
        default=None,
        alias="os.version",
        serialization_alias="os.version",
    )
    os_features: list[str] | None = pydantic.Field(
        default=None,
        alias="os.features",
        serialization_alias="os.features",
    )
    variant: str | None = None
    features: list[str] | None = None

    model_config = pydantic.ConfigDict(
        extra="allow",
        serialize_by_alias=True,
    )


class Descriptor(pydantic.BaseModel):
    media_type: str = pydantic.Field(
        alias="mediaType",
        serialization_alias="mediaType",
    )
    digest: str
    size: int

    urls: list[pydantic.HttpUrl] | None = None
    annotations: dict[str, str] | None = None
    platform: Platform | None = None

    model_config = pydantic.ConfigDict(
        extra="allow",
        serialize_by_alias=True,
    )


class ImageManifest(pydantic.BaseModel):
    schema_version: Literal[2] = pydantic.Field(
        default=2,
        alias="schemaVersion",
        serialization_alias="schemaVersion",
    )
    media_type: str = pydantic.Field(
        default="application/vnd.oci.image.manifest.v1+json",
        alias="mediaType",
        serialization_alias="mediaType",
    )

    config: Descriptor
    layers: list[Descriptor]

    model_config = pydantic.ConfigDict(
        extra="allow",
        serialize_by_alias=True,
    )


class ImageIndex(pydantic.BaseModel):
    schema_version: Literal[2] = pydantic.Field(
        default=2,
        alias="schemaVersion",
        serialization_alias="schemaVersion",
    )
    media_type: str = pydantic.Field(
        default="application/vnd.oci.image.index.v1+json",
        alias="mediaType",
        serialization_alias="mediaType",
    )

    manifests: list[Descriptor]

    annotations: dict[str, str] | None = None

    model_config = pydantic.ConfigDict(
        extra="allow",
        serialize_by_alias=True,
    )
