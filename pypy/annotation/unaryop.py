"""
Unary operations on SomeValues.
"""

from pypy.annotation.pairtype import pair
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeList, SomeDict
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeBuiltin, SomeClass
from pypy.annotation.model import SomeFunction, SomeMethod, SomeIterator
from pypy.annotation.model import immutablevalue, decode_simple_call
from pypy.annotation.model import unionof, set, setunion, missing_operation
from pypy.annotation.factory import BlockedInference, getbookkeeper
from pypy.annotation.factory import InstanceFactory, FuncCallFactory


UNARY_OPERATIONS = set(['len', 'is_true', 'getattr', 'setattr', 'call',
                        'iter', 'next'])

for opname in UNARY_OPERATIONS:
    missing_operation(SomeObject, opname)


class __extend__(SomeObject):
    
    def len(obj):
        return SomeInteger(nonneg=True)

    def is_true(obj):
        return SomeBool()

    def getattr(obj, s_attr):
        # get a SomeBuiltin if the SomeObject has
        # a corresponding method to handle it
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            analyser = getattr(obj.__class__, 'method_' + attr, None)
            if analyser is not None:
                return SomeBuiltin(analyser, obj)
        return SomeObject()

    def classattribute(obj, classdef):
        return obj   # default unbound __get__ implementation


class __extend__(SomeTuple):

    def len(tup):
        return immutablevalue(len(tup.items))


class __extend__(SomeDict):

    def len(dic):
        return immutablevalue(len(dic.items))


class __extend__(SomeList):

    def method_append(lst, s_item):
        pair(lst, SomeInteger()).setitem(s_item)

    def iter(lst):
        return SomeIterator(lst.s_item)


class __extend__(SomeIterator):

    def next(itr):
        return itr.s_item


class __extend__(SomeInstance):

    def currentdef(ins):
        if ins.revision != ins.classdef.revision:
            #print ins.revision, ins.classdef.revision
            raise BlockedInference
        return ins.classdef

    def getattr(ins, s_attr):
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            #print 'getattr:', ins, attr, ins.classdef.revision
            # look for the attribute in the MRO order
            for clsdef in ins.currentdef().getmro():
                if attr in clsdef.attrs:
                    # XXX we can't see the difference between function objects
                    # XXX on classes or on instances, so this will incorrectly
                    # XXX turn functions read from instances into methods
                    return clsdef.attrs[attr]
            # maybe the attribute exists in some subclass? if so, lift it
            clsdef = ins.classdef
            clsdef.generalize(attr, SomeImpossibleValue(), getbookkeeper())
            raise BlockedInference
        return SomeObject()

    def setattr(ins, s_attr, s_value):
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
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
            clsdef.generalize(attr, s_value, getbookkeeper())
            raise BlockedInference
        return SomeObject()


class __extend__(SomeBuiltin):

    def call(bltn, args, kwds):
        # decode the arguments and forward the analysis of this builtin
        arglist = decode_simple_call(args, kwds)
        if arglist is not None:
            if bltn.s_self is not None:
                arglist.insert(0, bltn.s_self)
            return bltn.analyser(*arglist)
        else:
            return SomeObject()


class __extend__(SomeClass):

    def call(cls, args, kwds):
        # XXX flow into __init__
        factory = getbookkeeper().getfactory(InstanceFactory)
        return factory.create(cls.cls)


class __extend__(SomeFunction):

    def call(fun, args, kwds):
        arglist = decode_simple_call(args, kwds)
        assert arglist is not None
        factory = getbookkeeper().getfactory(FuncCallFactory)
        results = [factory.pycall(func, arglist) for func in fun.funcs]
        return unionof(*results)

    def classattribute(fun, classdef):   # function -> unbound method
        d = {}
        for func in fun.funcs:
            d[func] = classdef
        return SomeMethod(d)


class __extend__(SomeMethod):

    def call(met, args, kwds):
        arglist = decode_simple_call(args, kwds)
        #print 'methodcall:', met, arglist
        assert arglist is not None
        factory = getbookkeeper().getfactory(FuncCallFactory)
        results = []
        for func, classdef in met.meths.items():
            # create s_self and record the creation in the factory
            s_self = SomeInstance(classdef)
            classdef.instancefactories[factory] = True
            # call func(s_self, *arglist)
            results.append(factory.pycall(func, [s_self]+arglist))
        return unionof(*results)
