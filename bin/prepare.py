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
COMMON = 'common.yaml'
DEF_PROPS = ['$id', '$schema', 'allOf']
P_PROPS = 'properties'
P_PROP_NAMES = 'propertyNames'
P_PROPS_ADD = 'unevaluatedProperties'
...

REF_RGX = compile(r'#.*$')
...

def GetDirs() -> Generator[Path, None, None]:
	def HasDirs(directory: Path) -> bool:
		return len([ *directory.glob(GLOB_META) ]) > 0
	
	directories = sorted(Path(LIB).glob('**'), reverse=True)

	yield from (
		directory
		for directory in directories
		if HasDirs(directory)
	)

def DelProperties(schema: dict, *props: str) -> None:
	for prop in props:
		try:
			del schema[prop]
		except KeyError:
			continue

def GetMaxRevision() -> int:
	return max((
		GetRevision(path.name)
		for path in Path(LIB).glob('rev.*.yaml')
	))

@lru_cache
def GetRevision(name: str) -> int:
	parts = str(name).split('.')
	revision = parts[1]
	return int(revision)

@lru_cache
def CompareRevisions(a: str, b: str) -> bool:
	return GetRevision(b) >= GetRevision(a)

@lru_cache
def FindMeta(path: Path | str) -> Path:
	meta = None
	metas = sorted(Path('.').glob(GLOB_META))
	for meta_path in metas:
		if not CompareRevisions(meta_path.name, path.name):
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

def PrepRevisions(directory: Path) -> None:
	with chdir(directory):
		for path in sorted(Path('.').glob(GLOB_REV)):
			path = path.absolute()
			rel  = path.relative_to(CWD)
			...

			print(f'Preparing \033[36m{rel}\033[0m ', end='')
			...

			meta_path = FindMeta(path)
			meta = GetMeta(meta_path.absolute())
			schema = GetSchema(path)
			...

			DelProperties(meta, *DEF_PROPS)
			...

			comp = CommentedMap()
			additional: bool = meta.get(P_PROPS_ADD, True)
			...

			allOf: list[dict] = schema['allOf']
			props: dict = None
			for scheme in allOf:
				if not 'meta.' in scheme.get('$ref', ''):
					props: dict = scheme
					break
			...

			if props:
				if P_PROPS in props and not additional:
					comp[P_PROP_NAMES] = CommentedMap()
					comp[P_PROP_NAMES]['enum'] = sorted([
						prop for prop, value in
							props[P_PROPS].items()
								if '/Deprecated' not in GetSchema(GetRef(value)).get('$ref', '')
					])
				...

				for prop, value in props.items():
					if not prop in [ P_PROP_NAMES, *DEF_PROPS, *meta ]:
						comp[prop] = value
				...
			...
			
			DelProperties(schema, *[ *meta.keys(), *comp.keys() ])
			...

			schema['allOf'] = [ { '$ref': f'./{meta_path}' }, comp ]
			schema["$id"] = f'https://github.com/LeShaunJ/ops-schema/blob/main/{rel}'.strip()
			...

			print(f'-> \033[35m{meta_path}\033[0m')
			if DRY_RUN:
				YML.dump(schema, sys.stdout)
				print('')
			else:
				with open(path, "w") as file:
					YML.dump(schema, file)
			...
...

def PrepCommon():
	max_rev = GetMaxRevision()
	common_path = Path(f'{LIB}/{COMMON}')
	common_schema = GetSchema(common_path)
	common_schema['properties']['revision'] |= {
		'minimum': 1,
		'maximum': max_rev,
		'default': max_rev,
	}
	...

	if DRY_RUN:
		YML.dump(common_schema['properties'], sys.stdout)
		print('')
	else:
		with open(common_path, "w") as file:
			YML.dump(common_schema, file)

YML = YAML()
YML.width = 255
...

with chdir(CWD): 
	[ PrepRevisions(dir) for dir in GetDirs() ]
	...

	PrepCommon()
	...
...
