#!/usr/bin/env python
import json
import os

from queck.model_utils import RefAdderJsonSchema
from queck.queck_models import Queck
from queck.quiz_models import Quiz

os.makedirs("schema", exist_ok=True)
with open("schema/quiz_schema.json", "w") as f:
    json.dump(Quiz.model_json_schema(), f, indent=2)

with open("schema/queck_schema.json", "w") as f:
    json.dump(Queck.model_json_schema(schema_generator=RefAdderJsonSchema), f, indent=2)
