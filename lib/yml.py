#!/usr/bin/env python3
from . import config as _Config
from pathlib import Path
from typing import TypeAlias, Type, Generator
from ruamel.yaml import YAML as _YAML, representer
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.compat import StringIO
...

_YML = _YAML()
_YML.explicit_start = True
_YML.explicit_end   = True
_YML.representer.add_representer(
	type(None),
	lambda self, _: self.represent_scalar('tag:yaml.org,2002:null', 'null')
)
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

def Render(schema: CommentedMap) -> str:
	stream = StringIO()
	_YML.dump(schema, stream)
	return stream.getvalue()

def Save(schema: CommentedMap, path: Path) -> None:
	if _Config.Flag.DRY_RUN:
		print(f'\n{Render(schema)}')
	else:
		with open(path, 'w') as file:
			_YML.dump(schema, file)
...
