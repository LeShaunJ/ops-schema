#!/usr/bin/env python3
import sys, re, json as JSN
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
GIT = 'https://github.com/LeShaunJ/ops-schema/blob/main'
COMMON = 'common.yaml'
OPS_JSN = 'ops.schema.json'

CAPTURE = False
...

def Pretty(schema) -> str:
	return JSN.dumps(schema, indent='  ')

def CreateSchema(content: dict) -> Resource:
	return Resource(
    contents=content,
    specification=DRAFT7,
	)

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

	return { **schema, **ref }

def AllOf(schema: dict, resolution: Resolved[dict]) -> dict:
	try:
		prop = 'allOf'
		others = reversed(schema[prop])
		...

		DelProperties(schema, prop)
		...

		return reduce(
			lambda schema1, schema2: { 
				**schema1,
				**Walk(schema2, resolution)
			},
			others, schema
		)
	except (KeyError, TypeError):
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

@overload
def Walk(resolution: Resolved[dict]) -> dict: ...
@overload
def Walk(composition: list[dict], resolution: Resolved[dict]) -> dict: ...
@overload
def Walk(schema: dict, resolution: Resolved[dict]) -> dict: ...
def Walk(*args) -> dict:
	global definitions
	...

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
		if 'definitions' in schema:
			schema_defs = Walk(schema['definitions'], resolution)
			definitions = { **definitions, **schema_defs }
			DelProperties(schema, 'definitions')
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

	registry.append({ 'allOf': [
		{
			'properties': { 'revision': { 'const': revision } },
			'required': ['revision']
		},
		{  '$ref': f'./{path}' }
	] })

def Compose() -> None:
	global registry
	registry.reverse()
	...

	print(f'Composing {OPS_JSN}... ', end='')
	...

	schema = CreateSchema({}).contents
	schema['$schema'] = 'https://json-schema.org/draft-07/schema'
	schema['$id'] = f'https://github.com/LeShaunJ/ops-schema/blob/main/{OPS_JSN}'
	schema['title'] = 'ops.yaml'
	schema['type'] = 'object'
	schema['description'] = 'Confirguration for `ops`'
	schema['minProperties'] = 1
	schema['if'] = { 'required': ['revision'] }
	schema['then'] = { 'oneOf': registry }
	schema['else'] = {
		'allOf': [
			{
    		'not': {
					'properties': { 'revision': {} },
					'required': ['revision']
				}
			},
    	{ '$ref': '#/then/oneOf/0/allOf/1' }
		]
	}
	...

	with open(OPS_JSN, 'w') as file:
		JSN.dump(schema, file, indent='  ')
	...

	print('Done!')
...

resolver = Registry(retrieve=RetrieveYAML).resolver()
registry = []
...

with chdir(CWD):
	common = GetCommon()
	paths = sorted(Path(LIB).glob('rev.*.yaml'))
	...

	for path in paths:
		jname = Path(path).with_suffix('.json')
		jpath = Path(f'{SRC}/{jname.name}')
		...

		print(f'Resolving {jpath}... ', end='')

		with open(jpath, 'w') as file:
			definitions = common.copy()
			schema = Walk(resolver.lookup(str(path)))
			schema['definitions'] = definitions
			schema['$id'] = f'{GIT}/{jpath}'
			...

			Register(jpath)
			...

			JSN.dump(schema, file, indent='  ')

		print('Done!')
	...

	Compose()
...
