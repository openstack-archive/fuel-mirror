# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os.path
import yaml

from fuel_mirror.tests import base


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


class TestValidateConfigs(base.TestCase):
    def test_validate_data_files(self):
        for f in os.listdir(DATA_DIR):
            with open(os.path.join(DATA_DIR, f), "r") as fd:
                data = yaml.load(fd)
                # TODO(add input data validation scheme)
                self.assertIn("groups", data)
                self.assertIn("fuel_release_match", data)
