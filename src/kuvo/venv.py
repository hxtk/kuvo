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

import pathlib
import subprocess  # noqa: S404


def build(rootfs: pathlib.Path) -> None:
    """Builds a self-contained environment under rootfs."""
    python = rootfs / "usr/local/python"
    app = rootfs / "app"
    env = {
        "UV_FROZEN": "1",
        "UV_NO_CACHE": "1",
        "UV_NO_DEV": "1",
        "UV_PYTHON_INSTALL_DIR": str(python),
        "UV_PROJECT_ENVIRONMENT": str(app),
        "UV_VENV_RELOCATABLE": "1",
    }
    subprocess.run(["uv", "sync"], env=env)  # noqa: S607
    bin_dir = app / "bin"
    _fix_shebangs(bin_dir, rootfs)
    app_py = bin_dir / "python"
    target = app_py.resolve().relative_to(app_py.parent, walk_up=True)
    app_py.unlink()
    app_py.symlink_to(target)


def _fix_shebangs(bin_dir: pathlib.Path, rootfs: pathlib.Path) -> None:
    for script in bin_dir.iterdir():
        if not script.is_file(follow_symlinks=False):
            continue

        text = script.read_text()

        if not text.startswith("#!"):
            continue

        lines = text.splitlines()
        shebang = pathlib.Path(lines[0][2:])
        if shebang.is_relative_to(rootfs):
            lines[0] = f"#!/{shebang.relative_to(rootfs)}"
            script.write_text("\n".join(lines) + "\n")
