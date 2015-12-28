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

from jsonschema import validate
from jsonschema import ValidationError
import yaml

from fuel_mirror.schemas.input_data_schema import SCHEMA
from fuel_mirror.tests import base


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


class TestValidateConfigs(base.TestCase):

    def test_validate_data_files(self):
        for f in os.listdir(DATA_DIR):
            with open(os.path.join(DATA_DIR, f), "r") as fd:
                data = yaml.load(fd)
                self.assertNotRaises(ValidationError, validate, data, SCHEMA)
                self.assertIn("groups", data)
                self.assertIn("fuel_release_match", data)

    def test_validate_fail_with_empty_data(self):
        self.assertRaises(ValidationError, validate, {}, SCHEMA)

    def test_validate_fail_without_groups(self):
        invalid_data = {
            "requirements": {
                "ubuntu": ["package_deb"]
            }
        }
        self.assertRaisesRegexp(
            ValidationError, "'groups' is a required property", validate,
            invalid_data, SCHEMA)

    def test_invalid_requirements_in_pattern_properies(self):
        invalid_data = {
            "requirements": {
                "ubun.tu": ["package_deb"]
            },
            "groups": {
            }
        }
        self.assertRaisesRegexp(
            ValidationError, "'ubun.tu' was unexpected", validate,
            invalid_data, SCHEMA)

    def test_invalid_requirements_type_array(self):
        invalid_data = {
            "requirements": {
                "ubuntu": "package_deb"
            },
            "groups": {
            }
        }
        self.assertRaisesRegexp(
            ValidationError, "'package_deb' is not of type 'array'", validate,
            invalid_data, SCHEMA)

    def test_invalid_inheritens_in_pattern_properies(self):
        invalid_data = {
            "inheritance": {
                "ubun.tu": "mos"
            },
            "groups": {
            }
        }
        self.assertRaisesRegexp(
            ValidationError, "'ubun.tu' was unexpected", validate,
            invalid_data, SCHEMA)

    def test_invalid_inheritens_type_string(self):
        invalid_data = {
            "inheritance": {
                "ubuntu": 123
            },
            "groups": {
            }
        }
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'string'", validate,
            invalid_data, SCHEMA)

    def test_invalid_groups_in_pattern_properies(self):
        invalid_data = {
            "groups": {
                "mo.s": []
            }
        }
        self.assertRaisesRegexp(
            ValidationError, "'mo.s' was unexpected", validate,
            invalid_data, SCHEMA)

    def test_invalid_groups_type_array(self):
        invalid_data = {
            "groups": {
                "mos": "string"
            }
        }
        self.assertRaisesRegexp(
            ValidationError, "'string' is not of type 'array'", validate,
            invalid_data, SCHEMA)

    def test_without_name_in_groups_array(self):
        invalid_data = {
            "groups": {
                "mos": [
                    {
                        'type': 'deb',
                        'uri': 'http://localhost/mos',
                        'priority': None,
                        'suite': 'mos$mos_version',
                        'section': 'main restricted'
                    }
                ]
            }
        }
        self.assertRaisesRegexp(
            ValidationError, "is not valid under any of the given schemas",
            validate, invalid_data, SCHEMA)

    def test_with_invalid_type_in_groups_array(self):
        invalid_data = {
            "groups": {
                "mos": [
                    {
                        'name': 'mos',
                        'type': 'adf',
                        'uri': 'http://localhost/mos',
                        'priority': None,
                        'suite': 'mos$mos_version',
                        'section': 'main restricted'
                    }
                ]
            }
        }
        self.assertRaisesRegexp(
            ValidationError, "is not valid under any of the given schemas",
            validate, invalid_data, SCHEMA)
