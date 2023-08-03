#!/usr/bin/env python3
import semver, config as Config, yml as YML
from pathlib import Path
from typing import overload, Generator, TypeAlias, TypeVar, Self
from ruamel.yaml.anchor import Anchor
from ruamel.yaml.comments import CommentedMap
from collections import OrderedDict
from contextlib import chdir
from functools import cache, lru_cache
...


T = TypeVar('T')
AnchorIterator: TypeAlias = Generator[tuple[str, Anchor], None, None]
SchemaIterator: TypeAlias = Generator[tuple[str, CommentedMap], None, None]
...


class Unsupported(Exception):
	...

class Change:
	@classmethod
	def IsScalar(cls: Self, value) -> bool:
		return isinstance(value, (str,int,float,bool))

	@classmethod
	def SameComplexity(cls: Self, base, other) -> bool:
		if isinstance(base, dict) and isinstance(other, dict):
			return True

		if isinstance(base, list) and isinstance(other, list):
			return True
		
		scalars = (str,int,float,bool)

		if isinstance(base, scalars) and isinstance(other, scalars):
			return True

		return False

	@classmethod
	def Merge(cls: Self, base, other: T) -> T:
		if not cls.SameComplexity(base, other):
			return other
		
		if cls.IsScalar(other):
			return other

		if isinstance(base, dict):
			constructor = type(base)
			return constructor({
				**base, **{
					k: cls.Merge(base.get(k, None), v)
						for k, v in other.items()
				}
			})

		if isinstance(base, list):
			constructor = type(base)
			return constructor([ *base, *other ])
		
		return None
		...

	@classmethod
	def MergeAll(cls: Self, first, *rest: T) -> T:
		from functools import reduce

		return reduce(
			lambda base, other: cls.Merge(base, other),
			rest, first
		)
...


@overload
def ID(path: Path) -> int: ...
@overload
def ID(anchor: Anchor) -> int: ...
@lru_cache()
def ID(*args: Path | str | Anchor) -> int:
	if isinstance(args[0], (Path, str)):
		parts = str(args[0]).split('.')
		revision = parts[1]
		return int(revision)
	...
	if isinstance(args[0], (Anchor,)):
		return int(args[0].value)
	...
	raise TypeError('Must specify Path | str | Anchor')

@lru_cache()
def Compare(a: Path | str, b: Path | str) -> bool:
	return ID(b) >= ID(a)

@cache
def Changes() -> CommentedMap:
	CHANGE_FILE = Config.Dir.File.CHANGES

	if CHANGE_FILE.exists():
		return YML.Get(CHANGE_FILE)
	
	return CommentedMap()

def Iterate() -> AnchorIterator:
	items: SchemaIterator = sorted(Changes().items())

	for revision, change in items:
		yield (revision, change.anchor)

@cache
def List() -> list[tuple[int, str, semver.Version]]:
	return [
		(revision, anchor.value, Parse(anchor.value))
			for revision, anchor in Iterate()
	]

@lru_cache()
def Parse(version: str) -> semver.Version:
	import re

	version = re.sub(r'^(\d+\.\d+\.\d+)\.?(\D.+)$', r'\1-\2', version)
	version = re.sub(r'(?<=\brc)(\d+)\b', lambda m: f'{m[1]:0>3}', version)

	return semver.Version.parse(version)

@cache
def Gems() -> OrderedDict[str, semver.Version]:
	import sys, pickle
	...

	GEM_NAME = Config.Git.GEM
	CACHE_DIR = Config.Cache.DIR
	CACHE_FILE = Config.Cache.FILE
	CACHE_UPDATE = Config.Flag.UPDATE
	...

	def retrieve() -> OrderedDict[str, semver.Version]:
		import re, subprocess as proc
		from operator import itemgetter

		command = ["gem","list","ops_team","--remote","--all","--pre"]

		result  = proc.run(command, text=True, capture_output=True)
		output  = result.stdout
		main_ln = re.findall(fr'(?<=^{GEM_NAME} [(]).+(?=[)])', output)

		result = [ (ver, Parse(ver)) for ver in main_ln[0].split(', ') ]
		result = sorted(result, key=itemgetter(1))

		return OrderedDict(result)
	...
	
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

@lru_cache()
def Versions(revision: int, gem_ver: str, sem_ver: semver.Version) -> list[str]:
	LIB = Config.Dir.LIB
	VER_MAX = Config.Version.MAX
	...

	name = f'{revision:0>3}'
	filename = f'rev.{name}.yaml'
	root_path = Path(f'{LIB}/{filename}')
	root = YML.Get(root_path)
	...

	if not 'min_version' in YML.Dig(root, 'allOf',0,'properties'):
		raise Unsupported(f'Skipping `min_version` for revision {name}.')
	...

	try:
		next_ver = List()[revision][2]
	except (KeyError, IndexError):
		next_ver = VER_MAX

	allowed_vers = [
		gem_ver, *[ 
			o_ver
				for o_ver, o_sem in Gems().items()
					if (sem_ver < o_sem) and (o_sem < next_ver)
		]
	]
	allowed_vers.reverse()
	...

	return allowed_vers
...


if __name__ == "__main__":
	with chdir(Config.Dir.CWD):
		changes: list[CommentedMap] = [
			v for _k, v in sorted(Changes().items())
		]
		...

		for revision, gem_ver, sem_ver in List():
			try:
				versions = Versions(revision, gem_ver, sem_ver)
				print(f'Updating `min_version` for revision {revision:0>3}... ')

				change: CommentedMap = Change.MergeAll(*changes[0:revision-1])
				print(change)
				print(versions)
			except Unsupported as e:
				print(e)
		...
...
