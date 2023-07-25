#!/usr/bin/env python3
import sys, os
from pathlib import Path
from contextlib import chdir
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLStreamError

SWD = Path(__file__)
CWD = Path(f'{SWD.parent}/..')
YML = YAML()
CHANGE_FILE = Path('changes.yaml')

with chdir(CWD):
    if CHANGE_FILE.exists():
        changes: CommentedMap = YML.load(CHANGE_FILE)
        YML.dump(changes, sys.stdout)

...
