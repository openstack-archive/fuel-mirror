# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

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
                self.assertIn("osnames", data)
