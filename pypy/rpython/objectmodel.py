"""
This file defines utilities for manipulating objects in an
RPython-compliant way.
"""

import new


def instantiate(cls):
    "Create an empty instance of 'cls'."
    if isinstance(cls, type):
        return object.__new__(cls)
    else:
        return new.instance(cls)

def we_are_translated():
    return False
# annotation -> True


class FREED_OBJECT(object):
    def __getattribute__(self, attr):
        raise RuntimeError("trying to access freed object")
    def __setattribute__(self, attr, value):
        raise RuntimeError("trying to access freed object")


def free_non_gc_object(obj):
    assert getattr(obj.__class__, "_alloc_flavor_", False) == "", "trying to free regular object"
    obj.__dict__ = {}
    obj.__class__ = FREED_OBJECT
