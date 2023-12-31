#!/usr/bin/env python3
import sys, subprocess as proc, re, semver, pickle
from functools import reduce
from operator import itemgetter
from typing import Generator, Any
from pathlib import Path
from contextlib import chdir
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.anchor import Anchor
from ruamel.yaml.error import YAMLStreamError
from collections import OrderedDict
...

sys.exit(0)


SWD = Path(__file__)
CWD = Path(f'{SWD.parent}/..')
LIB = 'var/lib'
...

CACHE_DIR = '.scache'
CACHE_FILE = f'{CACHE_DIR}/gem_versions'
CACHE_UPDATE = '-U' in sys.argv[1:]
...

DRY_RUN = '--dry-run' in sys.argv[1:]
...

GEM_NAME = 'ops_team'
CHANGE_FILE = Path('changes.yaml')
...

VER_MIN = semver.Version(0)
VER_MAX = semver.Version(9999999)
VER_REF = '../common.yaml#/definitions/SemVer'
VER_DIR = f'{LIB}/min_version'
...


def Dig(schema: CommentedMap, *paths: str | int) -> CommentedMap:
	return reduce(
		lambda schema, prop: schema[prop],
		paths, schema
	)

def GetRevision(anchor: Anchor) -> int:
	return int(anchor.value)

def IterRevisions(changes: CommentedMap) -> Generator[tuple[str, Anchor], None, None]:
	items: Generator[tuple[str, CommentedMap], None, None] = sorted(changes.items())
	for revision, change in items:
		yield (revision, change.anchor)

def GetRevisionVersions(changes: CommentedMap) -> list[tuple[int, str, semver.Version]]:
	return [
		(revision, anchor.value, ParseGemVersion(anchor.value))
			for revision, anchor in IterRevisions(changes)
	]

def ExtractGemVersion(version: str) -> semver.Version:
	return re.sub(r'^(\d+\.\d+\.\d+)(?:\D.*)?$', r'\1', version)

def ParseGemVersion(version: str) -> semver.Version:
	return semver.Version.parse(ExtractGemVersion(version))

def GetGemVersions() -> OrderedDict[str, semver.Version]:
	def retrieve() -> OrderedDict[str, semver.Version]:
		command = ["gem", "list", "ops_team", "--remote", "--all", "--pre"]

		result  = proc.run(command, text=True, capture_output=True)
		output  = result.stdout
		main_ln = re.findall(fr'(?<=^{GEM_NAME} [(]).+(?=[)])', output)

		result = [ (ExtractGemVersion(ver), ParseGemVersion(ver)) for ver in main_ln[0].split(', ') ]
		result = sorted({ *result }, key=itemgetter(1))

		print(result)

		return OrderedDict(result)
	
	if not CACHE_UPDATE and Path(CACHE_FILE).exists():
		with open(CACHE_FILE, 'rb') as file:
			return pickle.load(file)
	else:
		print('Retrieving gem versions...', file=sys.stderr)
		Path(CACHE_DIR).mkdir(exist_ok=True)
		vers = retrieve()
		with open(CACHE_FILE, 'wb') as file:
			pickle.dump(vers, file)
		return vers

def GetSchema(path: Path, default: bool = False) -> CommentedMap:
	if not default or path.exists():
		return YML.load(path)
	else:
		try:
			meta = list(Path(VER_DIR).glob('meta.*.yaml'))[0]
		except IndexError:
			meta = ""

		return YML.load(meta)
	
def SaveSchema(schema: CommentedMap, path: Path) -> None:
	if DRY_RUN:
		print('')
		YML.dump(schema, sys.stdout)
	else:
		with open(path, 'w') as file:
			YML.dump(schema, file)
...


YML = YAML(typ=['rt', 'string'])
YML.width = 255
...


with chdir(CWD):
	Versions = GetGemVersions()

	if CHANGE_FILE.exists():
		changes: CommentedMap = YML.load(CHANGE_FILE)

		RevisionVersions = GetRevisionVersions(changes)

		for revision, gem_ver, sem_ver in RevisionVersions:
			name = f'{revision:0>3}'
			change: CommentedMap = changes[revision]
			filename = f'rev.{name}.yaml'
			metaname = f'meta.017.yaml'
			path = Path(f'{VER_DIR}/{filename}')
			root_path = Path(f'{LIB}/{filename}')
			root = GetSchema(root_path)
			...

			if not 'min_version' in Dig(root, 'allOf',0,'properties'):
				print(f'Skipping `min_version` for revision {name}.')
				continue
			...

			print(f'Updating `min_version` for revision {name}... ', end='')
			...

			try:
				next_ver = RevisionVersions[revision][2]
			except (KeyError, IndexError):
				next_ver = VER_MAX

			allowed_vers = [
				ExtractGemVersion(gem_ver), 
				*[
					o_ver for o_ver, o_sem in Versions.items()
						if sem_ver < o_sem and o_sem < next_ver
				]
			]
			allowed_vers.reverse()
			...

			schema = GetSchema(path, Path(f'{VER_DIR}/{metaname}'))

			schema['$id'] = f'https://github.com/LeShaunJ/ops-schema/blob/main/{path}'
			schema['default'] = allowed_vers[0]
			schema['allOf'] = [
				{ 'enum': allowed_vers },
				{ '$ref': f'./{metaname}' },
				{ '$ref': VER_REF },
			]
			SaveSchema(schema, path)
			...

			root_ref = f'./{path.relative_to(LIB)}'
			Dig(root, 'allOf',0,'properties','min_version')['$ref'] = root_ref
			SaveSchema(root, root_path)
			...

			print('Done!')
...
