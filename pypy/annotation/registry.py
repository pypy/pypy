"""
A registry for objects that we cannot translate.

Reason: building extension modules.

This is a first attempt to have a way to declare what
we cannot translate, but want to get handled in some way.
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
