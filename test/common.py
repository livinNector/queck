from pathlib import Path

import yaml

FIXTURE_ROOT = Path(__file__).parent


def load_fixture(file_name):
    return yaml.safe_load((FIXTURE_ROOT/ 'fixtures' / file_name).read_text())

