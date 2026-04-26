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

"""Settings defines the configuration options for Kuvo."""

import dataclasses
import pathlib
import tomllib
from typing import Any
from typing import Final


@dataclasses.dataclass(frozen=True)
class Config:
    """Configuration settings for Kuvo.

    Attrs:
        oci_path: The output OCI layout directory.
        base: The OCI base image for this image.
        entrypoint: The OCI entrypoint as a list of arguments.
        cmd: The OCI command as a list of arguments.
    """

    oci_path: str
    base: str
    entrypoint: list[str] | None
    cmd: list[str] | None


DEFAULT: Final[Config] = Config(
    oci_path="build/oci",
    base="gcr.io/distroless/cc-debian13:nonroot",
    entrypoint=None,
    cmd=None,
)


def get_config() -> Config:
    """Get a configuration for Kuvo."""
    with pathlib.Path("pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)
    if "tool.kuvo" not in pyproject:
        return DEFAULT

    settings = pyproject["tool.kuvo"]
    if not isinstance(settings, dict):
        return DEFAULT

    return dataclasses.replace(
        DEFAULT,
        **{k.replace("-", "_"): v for k, v in settings.items()},
    )
