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

import json
import pathlib
import unittest

from kuvo.oci import models

TEST_INDEX = pathlib.Path(__file__).parent / "test_index.json"
INDEX_TEXT = TEST_INDEX.read_text()


class TestImageIndex(unittest.TestCase):
    """Test parsing and serialization of the ImageIndex model."""

    maxDiff = 10_000

    def test_roundtrip_pydantic(self) -> None:
        """Test round-trip through pydantic's validate_json and dump_json."""
        m = models.ImageIndex.model_validate_json(INDEX_TEXT)
        want = json.loads(INDEX_TEXT)
        got = json.loads(m.model_dump_json(exclude_none=True))
        self.assertEqual(want, got)
