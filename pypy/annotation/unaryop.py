"""
Unary operations on SomeValues.
"""

from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeList
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeBuiltin, SomeClass
from pypy.annotation.model import SomeFunction
from pypy.annotation.model import immutablevalue, decode_simple_call
from pypy.annotation.model import set, setunion, missing_operation
from pypy.annotation.factory import BlockedInference, getbookkeeper
from pypy.annotation.factory import InstanceFactory, FuncCallFactory


UNARY_OPERATIONS = set(['len', 'is_true', 'getattr', 'setattr', 'call'])

for opname in UNARY_OPERATIONS:
    missing_operation(SomeObject, opname)


class __extend__(SomeObject):
    
    def len(obj):
        return SomeInteger(nonneg=True)

    def is_true(obj):
        return SomeBool()

    def getattr(obj, attr):
        # get a SomeBuiltin if the object has a corresponding method
        if attr.is_constant() and isinstance(attr.const, str):
            attr = attr.const
            if hasattr(obj, 'method_' + attr):
                return SomeBuiltin(getattr(obj, 'method_' + attr))
        return SomeObject()


class __extend__(SomeTuple):

    def len(tup):
        return immutablevalue(len(tup.items))


class __extend__(SomeList):

    def method_append(lst, s_item):
        pair(lst, SomeInteger()).setitem(s_item)


class __extend__(SomeInstance):

    def currentdef(ins):
        if ins.revision != ins.classdef.revision:
            #print ins.revision, ins.classdef.revision
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


class __extend__(SomeBuiltin):

    def call(meth, args, kwds):
        # decode the arguments and forward the analysis of this builtin
        arglist = decode_simple_call(args, kwds)
        if arglist is not None:
            return meth.analyser(*arglist)
        else:
            return SomeObject()


class __extend__(SomeClass):

    def call(cls, args, kwds):
        # XXX flow into __init__
        factory = getbookkeeper().getfactory(InstanceFactory, cls.cls)
        return factory.create()


class __extend__(SomeFunction):

    def call(fun, args, kwds):
        arglist = decode_simple_call(args, kwds)
        assert arglist is not None
        factory = getbookkeeper().getfactory(FuncCallFactory)
        s_result = SomeImpossibleValue()
        for func in fun.funcs:
            s_next_result = factory.pycall(func, arglist)
            s_result = pair(s_result, s_next_result).union()
        return s_result
