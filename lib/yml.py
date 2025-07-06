#!/usr/bin/env python3
from . import config as _Config
from pathlib import Path
from typing import TypeAlias, Type, Generator
from ruamel.yaml import YAML as _YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
...

_YML = _YAML()
_YML.width = 255
...

# Scalar: TypeAlias = str | int | float | bool | None
# Mapping: TypeAlias = dict[str, ]
# Complex: TypeAlias = 
...

def Dig(schema: CommentedMap, *paths: str | int) -> CommentedMap:
	from functools import reduce

	return reduce(
		lambda schema, prop: schema[prop],
		paths, schema
	)

def Items(schema: dict | list) -> Generator[tuple[str, dict], None, None] | Generator[tuple[int, dict], None, None]:
	if isinstance(schema, dict):
		yield from schema.items()
	if isinstance(schema, list):
		yield from enumerate(schema)
	yield from ()

def Get(path: Path, default: bool = False) -> CommentedMap:
	if not default or path.exists():
		return _YML.load(path)
	else:
		try:
			VER_DIR = _Config.Version.DIR
			META_GLOB = _Config.Dir.Glob.META

			meta = list(Path(VER_DIR).glob(META_GLOB))[0]
		except IndexError:
			meta = ""

		return _YML.load(meta)
	
def Save(schema: CommentedMap, path: Path) -> None:
	if _Config.Flag.DRY_RUN:
		import sys

		print('')
		_YML.dump(schema, sys.stdout)
	else:
		with open(path, 'w') as file:
			_YML.dump(schema, file)
...
