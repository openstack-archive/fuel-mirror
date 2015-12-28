SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
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
        "packages": {
            "type": "array",
            "items":
                {
                    "type": "string",
                }
        },
        "repos": {
            "type": "array",
            "items": {
                "anyOf": [
                    {
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
                    {
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
                    }
                ]
            }
        },
        "requirements": {
            "type": "object",
                "properties": {
                    "centos": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                }
        },
        "groups": {"anyOf": [{
            "additionalProperties": {
                "type": "array",
                        "items": {

                            "type": "object",
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
                        }

            }
        }, {
            "type": "object",

            "additionalProperties": {
                "type": "array",
                        "items": {

                            "type": "object",
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
                        }

            }
        },
        ]
        },
        "inheritance": {
            "type": "object",
                "properties": {
                    "centos": {
                        "type": "string"
                    }
                }
        }
    },
    "required": [
        "groups",
    ]
}
