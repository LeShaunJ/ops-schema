#!/usr/bin/env python3
import sys
from typing import Generator
from pathlib import Path
from collections import OrderedDict
from contextlib import chdir
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLStreamError
from functools import lru_cache
from re import compile
...

GLOB_META = 'meta.*.yaml'
GLOB_REV = 'rev.*.yaml'
...

O_DRUN = '--dry-run'
DRY_RUN = O_DRUN in sys.argv[1:]
if DRY_RUN:
	sys.argv.remove(O_DRUN)
...

CWD = Path.cwd()
LIB = 'var/lib'
DEF_PROPS = ['$id', '$schema', 'allOf']
P_PROPS = 'properties'
P_PROP_NAMES = 'propertyNames'
P_PROPS_ADD = 'unevaluatedProperties'
...

REF_RGX = compile(r'#.*$')
...

def GetDirs() -> Generator[Path, None, None]:
	def HasDirs(directory: Path) -> bool:
		return len([ *directory.glob('**') ]) > 1
	
	directories = sorted(Path(LIB).glob('**'), reverse=True)

	for directory in directories:
		if HasDirs(directory):
			yield directory

def DelProperties(schema: dict, *props: str) -> None:
	for prop in props:
		try:
			del schema[prop]
		except KeyError:
			continue

@lru_cache
def GetRevision(path: Path | str) -> int:
	parts = str(path).split('.')
	revision = parts[1]
	return int(revision)

@lru_cache
def CompareRevisions(a: Path | str, b: Path | str) -> bool:
	return GetRevision(b) >= GetRevision(a)

@lru_cache
def FindMeta(path: Path | str) -> Path:
	meta = None
	metas = sorted(Path('.').glob(GLOB_META))
	for meta_path in metas:
		if not CompareRevisions(meta_path.absolute(), path):
			break
		meta = meta_path
	...
	if meta is None:
		raise FileNotFoundError(f'Could not find meta schema for {path}')
	...
	return meta

@lru_cache
def GetMeta(path: Path | str) -> CommentedMap:
	try:
		meta = YML.load(path)
		return meta
	except YAMLStreamError:
		return CommentedMap()

@lru_cache
def GetSchema(path: Path | str) -> CommentedMap:
	return YML.load(path)

def GetRef(schema: dict) -> Path:
	path = REF_RGX.sub(r'', schema.get('$ref', ''))
	return Path(path).absolute()

def Prepare(directory: Path) -> None:
	with chdir(directory):
		for path in sorted(Path('.').glob(GLOB_REV)):
			path = path.absolute()
			rel  = path.relative_to(CWD)
			...

			print(f'Preparing {rel}... ', end='')
			...

			meta_path = FindMeta(path)
			meta = GetMeta(meta_path.absolute())
			schema = GetSchema(path)
			...

			DelProperties(meta, *DEF_PROPS)
			...

			comp = CommentedMap()
			additional: bool = meta.get(P_PROPS_ADD, True)

			if P_PROPS in schema['allOf'][0] and not additional:
				comp[P_PROP_NAMES] = CommentedMap()
				comp[P_PROP_NAMES]['enum'] = sorted([
					prop for prop, value in
						schema['allOf'][0][P_PROPS].items()
							if '/Deprecated' not in GetSchema(GetRef(value)).get('$ref', '')
				])

			for prop, value in schema['allOf'][0].items():
				if not prop in [ P_PROP_NAMES, *DEF_PROPS, *meta ]:
					comp[prop] = value
			...
			
			DelProperties(schema, *[ *meta.keys(), *comp.keys() ])
			...

			schema['allOf'] = [ comp, { '$ref': f'./{meta_path}' } ]
			schema["$id"] = f'https://github.com/LeShaunJ/ops-schema/blob/main/{rel}'.strip()
			...

			print(f'Prepared -> {meta_path}')
			if DRY_RUN:
				YML.dump(schema, sys.stdout)
				print('')
			else:
				with open(path, "w") as file:
					YML.dump(schema, file)
			...
...

YML = YAML()
YML.width = 255
...

with chdir(CWD): [
	Prepare(dir)
		for dir in GetDirs()
]
...
