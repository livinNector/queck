import os
from types import GenericAlias
from typing import TypeAliasType, TypeVar, Union, get_args, get_origin


def safe_write_file(file_name, content, extension=None, force=False):
    """Writes to a file without overwriting it."""
    if extension is not None:
        base, ext = os.path.splitext(file_name)
        file_name = f"{base}.{extension}"

    if os.path.exists(file_name) and not force:
        raise FileExistsError(f"{file_name} already exists. ")
    with open(file_name, "w") as f:
        f.write(content)


def write_file(file_name, content, extension=None):
    safe_write_file(file_name, content, extension, force=True)


class Merger:
    def __init__(self, extend_lists=True, extend_dicts=True):
        self.extend_lists = extend_lists
        self.extend_dicts = extend_dicts

    def merge(self, a, b):
        if isinstance(b, list):
            for i in range(min(len(a), len(b))):
                if not isinstance(b[i], (list, dict)):
                    a[i] = b[i]
                else:
                    self.merge(a[i], b[i])
            if self.extend_lists:
                a.extend(b[len(a) :])
        elif isinstance(b, dict):
            a_keys = set(a.keys())
            for k in a_keys:
                if k in b:
                    if not isinstance(b[k], (list, dict)):
                        a[k] = b[k]
                    else:
                        self.merge(a[k], b[k])
            if self.extend_dicts:
                for k in b.keys():
                    if k not in a_keys:
                        a[k] = b[k]


def _unwrap_union(type_var, subs=None):
    if isinstance(type_var, GenericAlias):
        subs = dict(zip(get_origin(type_var).__type_params__, get_args(type_var)))
        return _unwrap_union(get_origin(type_var), subs)
    if isinstance(type_var, TypeAliasType):
        if get_origin(type_var.__value__) == Union:
            return Union[
                tuple(
                    _unwrap_union(inner_type, subs=subs)
                    for inner_type in get_args(type_var.__value__)
                )
            ]
        return _unwrap_union(type_var.__value__, subs=subs)
    if isinstance(type_var, TypeVar):
        subs = subs or {}
        return subs.get(type_var)
    return type_var


def get_literal_union_args(type):
    return list(map(lambda x: get_args(x)[0], (get_args(_unwrap_union(type)))))
