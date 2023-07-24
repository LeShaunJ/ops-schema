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
        return Yaml.load(path)
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

            try:
                props = schema['allOf'][1]
                schema.update(props)
                del schema['allOf']
            except (KeyError, IndexError):
                pass
            finally:
                meta.update(schema)
                schema = meta
                with open(path, "w") as file:
                    Yaml.dump(schema, file)
                path = path.absolute().relative_to(CWD)
                print(f'Fixed: {path} -> {meta_path}')
...
