"""
Unary operations on SomeValues.
"""

from types import FunctionType
from pypy.annotation.pairtype import pair
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeChar, SomeList, SomeDict
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeBuiltin 
from pypy.annotation.model import SomeCallable, SomeIterator
from pypy.annotation.model import SomePrebuiltConstant
from pypy.annotation.model import immutablevalue
from pypy.annotation.model import unionof, set, setunion, missing_operation
from pypy.annotation.factory import BlockedInference, getbookkeeper
from pypy.annotation.factory import CallableFactory, isclassdef 


UNARY_OPERATIONS = set(['len', 'is_true', 'getattr', 'setattr', 'simple_call',
                        'iter', 'next'])

for opname in UNARY_OPERATIONS:
    missing_operation(SomeObject, opname)


class __extend__(SomeObject):
    
    def len(obj):
        return SomeInteger(nonneg=True)

    def is_true(obj):
        if obj.is_constant():
            return immutablevalue(bool(obj.const))
        else:
            s_len = obj.len()
            if s_len.is_constant():
                return immutablevalue(s_len.const > 0)
            else:
                return SomeBool()

    def getattr(obj, s_attr):
        # get a SomeBuiltin if the SomeObject has
        # a corresponding method to handle it
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            analyser = getattr(obj.__class__, 'method_' + attr, None)
            if analyser is not None:
                return SomeBuiltin(analyser, obj)
            # if the SomeObject is itself a constant, allow reading its attrs
            if obj.is_constant() and hasattr(obj.const, attr):
                return immutablevalue(getattr(obj.const, attr))
        return SomeObject()

    def bindcallables(obj, classdef):
        return obj   # default unbound __get__ implementation


class __extend__(SomeBool):
    def is_true(self):
        return self

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


class __extend__(SomeString):

    def iter(str):
        return SomeIterator(SomeChar())


class __extend__(SomeChar):

    def len(chr):
        return immutablevalue(1)


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
                        clsdef.readonly[attr] = False
                        return   # already general enough, nothing to do
                    break
            else:
                # if the attribute doesn't exist yet, create it here
                clsdef = ins.classdef
            # create or update the attribute in clsdef
            clsdef.generalize(attr, s_value, getbookkeeper(), readonly=False)
            raise BlockedInference
        return SomeObject()

class __extend__(SomeBuiltin):
    def simple_call(bltn, *args):
        if bltn.s_self is not None:
            return bltn.analyser(bltn.s_self, *args)
        else:
            return bltn.analyser(*args)

class __extend__(SomeCallable):
    def simple_call(cal, *args):
        factory = getbookkeeper().getfactory(CallableFactory) 
        results = []
        for func, classdef in cal.callables.items():
            if isclassdef(classdef): 
                # create s_self and record the creation in the factory
                s_self = SomeInstance(classdef)
                classdef.instancefactories[factory] = True
                results.append(factory.pycall(func, s_self, *args))
            else:
                results.append(factory.pycall(func, *args))
        return unionof(*results) 

    def bindcallables(cal, classdef):   
        """ turn the callables in the given SomeCallable 'cal' 
            into bound versions.
        """
        d = cal.callables.copy()
        for func, value in cal.callables.items():
            if isinstance(func, FunctionType): 
                if isclassdef(value): 
                    print ("!!! rebinding an already bound"
                           " method %r with %r" % (func, value))
                d[func] = classdef
            else:
                d[func] = value 
        return SomeCallable(d)
                
    #def simple_call(fun, *args):
    #    factory = getbookkeeper().getfactory(CallableFactory)
    #    results = [factory.pycall(func, *args) for func in fun.funcs]
    #    return unionof(*results)


class __extend__(SomePrebuiltConstant):

    def getattr(pbc, s_attr):
        assert s_attr.is_constant()
        attr = s_attr.const
        bookkeeper = getbookkeeper()
        actuals = []
        for c in pbc.prebuiltinstances:
            bookkeeper.attrs_read_from_constants.setdefault(c, {})[attr] = True
            if hasattr(c, attr):
                actuals.append(immutablevalue(getattr(c, attr)))
        return unionof(*actuals)

    def setattr(pbc, s_attr, s_value):
        raise Exception, "oops!"
