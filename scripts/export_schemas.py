#!/usr/bin/env python
import json
import os

from queck.queck_models import Queck
from queck.quiz_models import Quiz

os.makedirs("schema", exist_ok=True)
with open("schema/quiz_schema.json", "w") as f:
    json.dump(Quiz.model_json_schema(), f, indent=2)

with open("schema/queck_schema.json", "w") as f:
    # workaround for updating refs
    f.write(json.dumps(Queck.model_json_schema(), indent=2).replace('"ref', '"$ref'))
