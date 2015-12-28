SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "definitions": {
        "DEB_REPO_SCHEMA": {
            "type": "object",
            "required": [
                "name",
                "uri",
                "suite",
                "section"
            ],
            "properties": {
                "name": {
                    "type": "string"
                },
                "type": {
                    "type": "string",
                    "enum": ["deb"]
                },
                "uri": {
                    "type": "string"
                },
                "priority": {
                    "anyOf": [
                        {
                            "type": "integer"
                        },
                        {
                            "type": "null"
                        }
                    ]
                },
                "suite": {
                    "type": "string"
                },
                "section": {
                    "type": "string"
                },
            }
        },
        "RPM_REPO_SCHEMA": {
            "type": "object",
            "required": [
                "name",
                "uri",
            ],
            "properties": {
                "name": {
                    "type": "string"
                },
                "type": {
                    "type": "string",
                    "enum": ["rpm"]
                },
                "uri": {
                    "type": "string"
                },
                "priority": {
                    "anyOf": [
                        {
                            "type": "integer"
                        },
                        {
                            "type": "null"
                        }
                    ]
                },
            }
        },
        "REPO_SCHEMA": {
            "anyOf":
            [
                {"$ref": "#/definitions/DEB_REPO_SCHEMA"},
                {"$ref": "#/definitions/RPM_REPO_SCHEMA"}
            ]
        },

        "REPOS_SCHEMA": {
            "type": "array", "items": {"$ref": "#/definitions/REPO_SCHEMA"}
        }
    },
    "type": "object",
    "required": [
        "groups",
    ],
    "properties": {
        "fuel_release_match": {
            "type": "object",
            "properties": {
                "operating_system": {
                    "type": "string"
                }
            },
            "required": [
                "operating_system"
            ]
        },
        "requirements": {
            "type": "object",
            "patternProperties": {
                "^[0-9a-z_-]+$": {"type": "array"}
            },
            "additionalProperties": False,
        },
        "groups": {
            "type": "object",
            "patternProperties": {
                "^[0-9a-z_-]+$": {"$ref": "#/definitions/REPOS_SCHEMA"}
            },
            "additionalProperties": False,
        },
        "inheritance": {
            "type": "object",
            "patternProperties": {
                "^[0-9a-z_-]+$": {"type": "string"}
            },
            "additionalProperties": False,
        }
    }
}
