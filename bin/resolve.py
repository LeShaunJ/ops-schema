#!/usr/bin/env python3
import sys, os, re, json as JSN
from collections import OrderedDict
from typing import overload, Any, Generator
from functools import reduce
from pathlib import Path
from contextlib import chdir
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from referencing import Registry, Resource
from referencing._core import Resolved, Resolver
from referencing.jsonschema import DRAFT7
...

SWD = Path(__file__)
CWD = Path(f'{SWD.parent}/..')
YML = YAML()
LIB = 'var/lib'
SRC = 'var/src'
TST = 'var/tests'
GIT = f"{str(os.environ['REMOTE']).removesuffix('.git')}/blob/main"
COMMON = 'common.yaml'
OPS_JSN = 'ops.schema.json'
...

CAPTURE = False
...

P_PROPS_ADD = 'unevaluatedProperties'
...

def Pretty(schema) -> str:
	return JSN.dumps(schema, indent='  ')

def CreateSchema(content: dict) -> Resource:
	return Resource(
    contents=content,
    specification=DRAFT7,
	)

def GetMaxRevision() -> int:
	try:
		with open('.revision', 'r') as file:
			return int(file.read())
	except:
		print(
			'[ERROR] Unable to determine max revision from `./.revision`',
			file=sys.stderr)

def GetURN(urn: str) -> tuple[Path, list[str]]:
	parts: list[str] = re.split(r'#\/?', urn) + ['']

	try:
		uri = Path(parts[0]).relative_to(GIT)
	except ValueError:
		uri = Path(parts[0])

	return uri, parts[1].split()

def GetCommon() -> dict:
	resolution = resolver.lookup(f'{LIB}/{COMMON}')
	schema: dict = resolution.contents
	defs: dict = schema.get('definitions', {})
	...

	return {
		name: Walk(schema, resolution)
			for name, schema in defs.items()
	}

def Dig(schema: dict, *paths: str) -> dict:
	return reduce(
		lambda schema, prop: schema[prop],
		paths, schema
	)

def DelProperties(schema: dict, *props: str) -> None:
	for prop in props:
		try:
			del schema[prop]
		except KeyError:
			continue

def RetrieveYAML(urn: str) -> Resolved[dict]:
	uri, path = GetURN(urn)
	schema = Dig(YML.load(uri), *path)
	...

	return CreateSchema(schema)

def HasRef(schema: dict) -> bool:
	return '$ref' in schema

def GetRef(schema: dict) -> str:
	return schema['$ref']

def SetRef(schema: dict, resolution: Resolved[dict]) -> dict:
	path = GetRef(schema)
	if '#/definitions' in path:
		schema['$ref'] = f"#{path.split('#')[1]}"
		...

		return schema
	...

	resolve = resolution.resolver.lookup(path)
	ref: dict = Walk(resolve)
	...

	DelProperties(ref, '$id', '$schema')
	DelProperties(schema, '$ref')
	...

	if "meta." in path:
		DelProperties(ref, P_PROPS_ADD)

	return { **schema, **ref }

def AllOf(schema: dict, resolution: Resolved[dict]) -> dict:
	try:
		prop = 'allOf'
		others: list[dict] = schema[prop]
		remaining: list[dict] = []
		...

		DelProperties(schema, prop)
		...

		allOf = {}
		for other in others:
			other = Walk(other, resolution)

			if HasRef(other):
				remaining.append(other)
			else:
				allOf = { **allOf, **other }
		...

		if remaining:
			schema[prop] = [ s for s in ( allOf, *remaining ) if s ]
		else:
			schema = allOf
		...
	except (KeyError, TypeError):
		pass
	finally:
		return schema

def GetItems(schema: dict | list) -> list[tuple[str, dict]] | list[tuple[int, dict]]:
	if isinstance(schema, dict):
		return schema.items()
	if isinstance(schema, list):
		return enumerate(schema)
	
	print(f'no iter: {schema}')

	return []

def HasIters(schema: dict) -> bool:
	return any([
		isinstance(val, (dict, list)) for val in schema.values()
	])

def GetIters(schema: dict) -> Generator[tuple[str, dict | list], None, None]:
	try:
		for key, val in GetItems(schema):
			if isinstance(val, (dict, list)):
				yield key, val
	except:
		print('')
		print(f'Schema: {Pretty(schema)}', file=sys.stderr)
		raise

def Define(schema: dict, resolution: Resolved[dict]) -> None:
	global definitions
	...
	
	prop = 'definitions'
	
	if prop in schema:
		schema_defs = Walk(schema[prop], resolution)
		definitions = { **definitions, **schema_defs }
		DelProperties(schema, prop)

@overload
def Walk(resolution: Resolved[dict]) -> dict: ...
@overload
def Walk(composition: list[dict], resolution: Resolved[dict]) -> dict: ...
@overload
def Walk(schema: dict, resolution: Resolved[dict]) -> dict: ...
def Walk(*args) -> dict:
	try:
		resolution: Resolved[dict] = args[1]
		schema: dict | list[dict] = args[0]
	except IndexError:
		resolution: Resolved[dict] = args[0]
		schema: dict | list[dict] = resolution.contents
	...

	if isinstance(schema, list):
		for prop, val in GetIters(schema):
			if isinstance(val, dict):
				schema[prop] = Walk(val, resolution)
	...

	if isinstance(schema, dict):
		Define(schema, resolution)
		...

		for prop, iter in GetIters(schema):
			if HasRef(iter):
				iter = Walk(iter, resolution)
			...

			for key, val in GetItems(iter):
				if isinstance(val, (dict, list)):
					schema[prop][key] = Walk(val, resolution)
			...
	...

	if HasRef(schema):
		schema = SetRef(schema, resolution)
	...

	schema = AllOf(schema, resolution)
	...
	
	return schema

def GetRevision(path: Path) -> int:
	parts = str(path).split('.')
	revision = parts[1]
	return int(revision)

def Register(path: Path) -> None:
	global registry
	...

	revision = GetRevision(path)
	...

	# registry.append({ "allOf": [
		# {
		# 	"properties": {
		# 		"revision": {
		# 			"title": "Revision",
		# 			"const": revision
		# 		}
		# 	},
		# 	"required": ["revision"]
   	# },
		# # {
		# 	# "if": { "required": ["min_version"] },
		# 	# "then": {
		# 		# "properties": {
		# 			# "min_version": {
		# 				# "enum": []
		# 			# }
		# 		# }
		# 	# }
		# # },
		# { "$ref": f"./{path}" }
	# ] })

	registry.append({
		"if": {
			"properties": {
				"revision": {
					"const": revision
				}
			}
		},
		"then": {
			"$ref": f"./{path}"
		}
	})

def Compose() -> None:
	global registry
	registry.reverse()
	comp_type = 'allOf'
	...

	print(f'Composing {OPS_JSN}... ', end='')
	...

	schema = CreateSchema({}).contents
	schema['$schema'] = 'http://json-schema.org/draft-07/schema'
	schema['$id'] = f'{GIT}/{OPS_JSN}'
	schema['title'] = 'ops.yaml'
	schema['type'] = 'object'
	schema['description'] = 'Confirguration for `ops`'
	schema['minProperties'] = 1
	schema['if'] = { 'required': ['revision'] }
	schema['then'] = { comp_type: registry }
	schema['else'] = {
		'allOf': [
			{
    		'not': {
					'properties': { 'revision': {} },
					'required': ['revision']
				}
			},
    	{ '$ref': f'#/then/{comp_type}/0/then' }
		]
	}
	...

	with open(OPS_JSN, 'w') as file:
		JSN.dump(schema, file, indent='  ')
	...

	print('Done!')
...

resolver = Registry(retrieve=RetrieveYAML).resolver()
registry: list[dict] = []
...

with chdir(CWD):
	current = GetMaxRevision()
	common = GetCommon()
	paths = sorted(Path(LIB).glob('rev.*.yaml'))
	...

	for path in paths:
		revision = GetRevision(path)
		if revision > current:
			break
		...

		jname = Path(path).with_suffix('.json')
		jpath = Path(f'{SRC}/{jname.name}')
		...

		print(f'Resolving {jpath}... ', end='')

		with open(jpath, 'w') as file:
			definitions = common.copy()
			...

			schema = OrderedDict([
				('$schema', 'https://json-schema.org/draft-07/schema'),
				('$id', f'{GIT}/{jpath}'),
				*Walk(resolver.lookup(str(path))).items(),
				('definitions', definitions),
			])
			...

			schema['title'] = 'ops.yaml'
			schema['description'] = f'Confirguration for `ops` (rev. {revision:03d})'
			schema['properties']['revision']['const'] = revision
			...

			Register(jpath)
			...

			JSN.dump(schema, file, indent='  ')
			file.write('\n')

		test = Path(f'{TST}/ops.{revision:03d}.yaml')
		if not test.exists():
			with test.open('w') as file:
				file.write('# yaml-language-server: $schema=../../ops.schema.json\n')
				file.write('---\n')
				file.write(f'revision: {revision}\n')
		...

		print('Done!')
		...
	...

	Compose()
...
