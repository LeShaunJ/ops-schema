#!/usr/bin/env python3
import sys
from pathlib import Path
from contextlib import chdir
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLStreamError

GLOB_META = 'meta.*.yaml'
GLOB_REV = 'rev.*.yaml'

def Getrevision(path: Path | str) -> int:
	parts = str(path).split('.')
	revision = parts[1]
	return int(revision)

def CompareRevisions(a: Path | str, b: Path | str) -> bool:
	# print(f'  {b.absolute()} >= {a.absolute()}', file=sys.stderr)
	return Getrevision(b) >= Getrevision(a)

def FindMeta(path: Path | str) -> Path | None:
	meta = None
	metas = sorted(Path('.').glob(GLOB_META))
	# print(f'\n{path.absolute()}:', file=sys.stderr)
	for meta_path in metas:
		if not CompareRevisions(meta_path, path):
			break
		meta = meta_path
	# print(f'  -> {meta.absolute()}', file=sys.stderr)
	return meta

def GetMeta(path: Path | str) -> CommentedMap:
	try:
		meta = Yaml.load(path)
		# del meta["$schema"]
		# del meta["$id"]
		return meta
	except (TypeError, YAMLStreamError):
		return CommentedMap()
	
def GetRevision(path: Path | str) -> CommentedMap:
	return Yaml.load(path)

Yaml = YAML()
CWD = Path.cwd()

for dir in reversed(sorted(sys.argv[1:])):
	with chdir(dir):
		for path in sorted(Path('.').glob(GLOB_REV)):
			meta_path = FindMeta(path)
			meta = GetMeta(meta_path)
			schema = GetRevision(path)

			meta.update(schema)
			schema = meta

			rel = path.absolute().relative_to(CWD)
			schema["$id"] = f'https://github.com/LeShaunJ/ops-schema/blob/main/{rel}'

			rev = Getrevision(path)
			schema["title"] = f'ops.yaml'

			with open(path, "w") as file:
				Yaml.dump(schema, file)

			print(f'Fixed: {rel} -> {meta_path}')
...
