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
        repositories: The OCI repositories to generate.
        tags: The OCI tag to generate.
    """

    oci_path: str
    base: str
    entrypoint: list[str] | None
    cmd: list[str] | None
    repositories: list[str] | None
    tags: list[str] | None
    arch: str = "amd64"
    os: str = "linux"


DEFAULT: Final[Config] = Config(
    oci_path="build/oci",
    base="gcr.io/distroless/cc-debian13:nonroot",
    entrypoint=None,
    cmd=None,
    repositories=["{name}"],
    tags=["latest", "v{version}"],
)


def get_config() -> Config:
    """Get a configuration for Kuvo."""
    try:
        with pathlib.Path("pyproject.toml").open("rb") as f:
            pyproject = tomllib.load(f)
    except FileNotFoundError:
        pyproject: dict[str, Any] = {}

    project = pyproject.get("project", {})
    if "kuvo" not in pyproject.get("tool", {}):
        print("No kuvo config.")
        return _render(DEFAULT, project)

    settings = pyproject.get("tool", {}).get("kuvo")
    if not isinstance(settings, dict):
        print("Kuvo config isn't a dict.")
        return _render(DEFAULT, project)

    replacements = {k.replace("-", "_"): v for k, v in settings.items()}
    return _render(
        dataclasses.replace(
            DEFAULT,
            **replacements,
        ),
        project,
    )


def _render(config: Config, project: dict[str, Any]) -> Config:
    project = _DotDict(project)

    repositories = config.repositories
    if repositories:
        repositories = [x.format_map(project) for x in repositories]

    tags = config.tags
    if tags:
        tags = [x.format_map(project) for x in tags]

    return dataclasses.replace(
        config,
        repositories=repositories,
        tags=tags,
    )


class _DotDict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
