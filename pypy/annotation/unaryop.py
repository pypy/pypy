"""
Unary operations on SomeValues.
"""

from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeList
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance
from pypy.annotation.model import set, setunion, missing_operation
from pypy.annotation.factory import BlockedInference


UNARY_OPERATIONS = set(['len', 'is_true', 'getattr', 'setattr'])

for opname in UNARY_OPERATIONS:
    missing_operation(SomeObject, opname)


class __extend__(SomeObject):
    
    def len(obj):
        return SomeInteger(nonneg=True)

    def is_true(obj):
        return SomeBool()


class __extend__(SomeInstance):

    def currentdef(ins):
        if ins.revision != ins.classdef.revision:
            print ins.revision, ins.classdef.revision
            raise BlockedInference()
        return ins.classdef

    def getattr(ins, attr):
        if attr.is_constant() and isinstance(attr.const, str):
            attr = attr.const
            # look for the attribute in the MRO order
            for clsdef in ins.currentdef().getmro():
                if attr in clsdef.attrs:
                    return clsdef.attrs[attr]
            # maybe the attribute exists in some subclass? if so, lift it
            clsdef = ins.classdef
            clsdef.generalize(attr, SomeImpossibleValue())
            raise BlockedInference(clsdef.getallfactories())
        return SomeObject()

    def setattr(ins, attr, s_value):
        if attr.is_constant() and isinstance(attr.const, str):
            attr = attr.const
            for clsdef in ins.currentdef().getmro():
                if attr in clsdef.attrs:
                    # look for the attribute in ins.classdef or a parent class
                    s_existing = clsdef.attrs[attr]
                    if s_existing.contains(s_value):
                        return   # already general enough, nothing to do
                    break
            else:
                # if the attribute doesn't exist yet, create it here
                clsdef = ins.classdef
            # create or update the attribute in clsdef
            clsdef.generalize(attr, s_value)
            raise BlockedInference(clsdef.getallfactories())
        return SomeObject()
