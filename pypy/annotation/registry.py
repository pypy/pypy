"""
A registry for objects that we cannot translate.

Reason: building extension modules.

A simple approach to support building extension modules.
The key idea is to provide a mechanism to record certain objects
and types to be recognized as SomeObject, to be created using imports
without trying to further investigate them.

This is intentionally using global dicts, since what we can
translate is growing in time, but usually nothing you want
to configure dynamically.
"""

import sys

from pypy.objspace.flow.objspace import NOT_REALLY_CONST
from pypy.objspace.flow.model import Constant

# this dictionary can be extended by extension writers
DEFINED_SOMEOBJECTS = { sys: True,
                        }

# this dict registers special import paths (not used right now)
IMPORT_HINTS = {}

def registerSomeObject(obj, specialimport=None):
    DEFINED_SOMEOBJECTS[obj] = True
    NOT_REALLY_CONST[Constant(obj)] = {} # disable all
    IMPORT_HINTS[obj] = specialimport

registerSomeObject(long)
registerSomeObject(file)

# we should do some automatic registration. And ideas?
