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
"""The main command line program for this application."""

import hashlib
import json
import pathlib
import tarfile
import tempfile

import click
import oras.client

from kuvo import oci
from kuvo import settings
from kuvo import venv


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    """Reproducible OCI images for your Python projects."""
    ctx.obj = settings.get_config()


@main.command()
@click.pass_context
def build(ctx: click.Context) -> None:
    """Build an OCI image for the current project."""
    ctx.ensure_object(settings.Config)
    out_path = pathlib.Path(ctx.obj.oci_path)
    oci.pull(out_path, ctx.obj.base)
    click.echo("Running the build...")
    with tempfile.TemporaryDirectory() as tdstr:
        click.echo(f"Using temporary directory {tdstr}")
        td = pathlib.Path(tdstr)
        venv.build(td)

        with tempfile.NamedTemporaryFile(
            suffix=".tar", mode="wb", delete_on_close=False
        ) as tmp:
            path = pathlib.Path(tmp.name)

            with tarfile.open(fileobj=tmp, mode="w") as tf:
                _package_tar(tf, rootfs=td, include=["usr"])
            tmp.close()

            oci.add_layer(out_path, path)

        with tempfile.NamedTemporaryFile(
            suffix=".tar", mode="wb", delete_on_close=False
        ) as tmp:
            path = pathlib.Path(tmp.name)

            with tarfile.open(fileobj=tmp, mode="w") as tf:
                _package_tar(tf, rootfs=td, include=["app"])
            tmp.close()

            oci.add_layer(out_path, path)

        oci.ensure_path(out_path, "/app/bin")


def _package_tar(
    tf: tarfile.TarFile, rootfs: pathlib.Path, include: list[str]
) -> None:
    paths: list[pathlib.Path] = []
    for path in include:
        paths += (rootfs / path).rglob("*")
    paths.sort()

    for path in paths:
        ti = tf.gettarinfo(str(path), arcname=str(path.relative_to(rootfs)))
        ti.uid = 0
        ti.gid = 0
        ti.uname = ""
        ti.gname = ""
        ti.mtime = 0

        if path.is_file():
            with pathlib.Path(path).open("rb") as f:
                tf.addfile(ti, f)
        else:
            tf.addfile(ti)


if __name__ == "__main__":
    main()
