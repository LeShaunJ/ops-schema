#!/usr/bin/env python3
import sys
from typing import Generator
from pathlib import Path
from collections import OrderedDict
from contextlib import chdir
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLStreamError
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

def GetRevision(path: Path | str) -> int:
	parts = str(path).split('.')
	revision = parts[1]
	return int(revision)

def CompareRevisions(a: Path | str, b: Path | str) -> bool:
	return GetRevision(b) >= GetRevision(a)

def FindMeta(path: Path | str) -> Path | None:
	meta = None
	metas = sorted(Path('.').glob(GLOB_META))
	for meta_path in metas:
		if not CompareRevisions(meta_path, path):
			break
		meta = meta_path
	return meta

def GetMeta(path: Path | str) -> CommentedMap:
	try:
		meta = YML.load(path)
		# del meta["$schema"]
		# del meta["$id"]
		return meta
	except (TypeError, YAMLStreamError):
		return CommentedMap()
	
def GetSchema(path: Path | str) -> CommentedMap:
	return YML.load(path)

def Prepare(directory: Path) -> None:
	with chdir(directory):
		for path in sorted(Path('.').glob(GLOB_REV)):
			rel = path.absolute().relative_to(CWD)
			...

			print(f'Preparing {rel}... ', end='')
			...

			meta_path = FindMeta(path)
			meta = GetMeta(meta_path)
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
							if '/Deprecated' not in value['$ref']
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
