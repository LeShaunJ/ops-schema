#!/usr/bin/env python3
import sys
from pathlib import Path
...

class Flag:
	@staticmethod
	def get(*names: str) -> bool:
		result = False

		for name in names:
			result = name in sys.argv[1:]
			if result:
				sys.argv.remove(name)
				break

		return result

	DRY_RUN = get('--dry-run')
	UPDATE  = get('-U')

class Dir:
	SWD = Path(__file__).parent
	CWD = Path(f'{SWD}/..')
	LIB = Path('var/lib')
	SRC = Path('var/src')

	class Glob:
		META = 'meta.*.yaml'
		REV  = 'rev.*.yaml'

	class File:
		COMMON  = Path('common.yaml')
		OPS_JSN = Path('ops.schema.json')
		CHANGES = Path('changes.yaml')

class Git:
	MAIN = 'https://github.com/LeShaunJ/ops-schema/blob/main'
	GEM  = 'ops_team'

class Keyword:
	DEFAULTS = ['$id', '$schema', 'allOf']
	PROPERTIES = 'properties'
	PROPERTY_NAMES = 'propertyNames'
	ADDITIONAL_PROPS = 'additionalProperties'

class Cache:
	DIR  = Path('.scache')
	FILE = DIR.joinpath('gem_versions')

class Version:
	import semver

	MIN = semver.Version(0)
	MAX = semver.Version(9999999)
	REF = '../common.yaml#/definitions/SemVer'
	DIR = Dir.LIB.joinpath('min_version')
...
