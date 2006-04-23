from pypy.translator.translator import TranslationContext
from pypy import conftest
from py.test import raises
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython import robject, rclass
from pypy.translator.tool.cbuild import enable_fast_compilation

import sys, types

P = not False  # debug printing

def get_annotation(func):
    argstypelist = []
    if func.func_defaults:
        for spec in func.func_defaults:
            if isinstance(spec, tuple):
                # use the first type only for the tests
                spec = spec[0]
            argstypelist.append(spec)
    missing = [object] * (func.func_code.co_argcount - len(argstypelist))
    return missing + argstypelist

def get_compiled_module(func, view=conftest.option.view, inline_threshold=1,
                use_boehm=False, exports=None):
    from pypy.translator.translator import TranslationContext
    from pypy.translator.backendopt.all import backend_optimizations

    from pypy.translator.c import gc
    from pypy.translator.c.genc import CExtModuleBuilder

    global _t # allow us to view later
    _t = t = TranslationContext(do_imports_immediately=False)
    ann = t.buildannotator()
    rtyper = t.buildrtyper()
    bk = rtyper.annotator.bookkeeper
    if not exports:
        exports = []
    all = [obj.__name__ for obj in exports]
    exports = exports + [('__all__', all)]

    ann.build_types(func, get_annotation(func))

    for obj in exports:
        if isinstance(obj, type):
            clsdef = bk.getuniqueclassdef(obj)
            rtyper.add_wrapper(clsdef)
        elif isinstance(obj, types.FunctionType):
            if not ann.bookkeeper.getdesc(obj).querycallfamily():
                # not annotated, so enforce it
                ann.build_types(obj, get_annotation(obj))

    if view:
        t.viewcg()
    rtyper.specialize()
    if view:
        t.viewcg()
    t.checkgraphs()

    gcpolicy = None
    if use_boehm:
        gcpolicy = gc.BoehmGcPolicy

    backend_optimizations(t, inline_threshold=inline_threshold)
    if view:
        t.viewcg()

    cbuilder = CExtModuleBuilder(t, func, gcpolicy=gcpolicy)
    # explicit build of database
    db = cbuilder.build_database(exports=exports)
    cbuilder.generate_source(db)
    if view:
        t.viewcg()
    cbuilder.compile()

    return cbuilder.import_module()

def getcompiled(func, *args, **kwds):
    module = get_compiled_module(func, *args, **kwds)
    return getattr(module, func.__name__)

# _______________________________________________-
# stubs for special annotation/rtyping


def wrap(thing):
    return thing # untranslated case

def unwrap(pyobj, typ):
    assert isinstance(pyobj, typ)
    return pyobj # untranslated case
unwrap._annspecialcase_ = 'specialize:arg(1)'


# XXX
# wrapping/unwrapping should be annotatable.
# Idea: create tunnel objects which share
# annotation across SomeObjectness, sharing a key!

class Entry(ExtRegistryEntry):
    _about_ = unwrap

    def compute_result_annotation(self, s_wrapped, s_spec):
        # this will go away, much better way found!
        assert hasattr(s_spec, 'descriptions'), 'need a class in unwrap 2nd arg'
        descs = s_spec.descriptions
        assert len(descs) == 1, 'missing specialisation, classdesc not unique!'
        for desc in descs.keys():
            classdef = desc.getuniqueclassdef()
        return annmodel.SomeInstance(classdef)

    def specialize_call(self, hop):
        v_obj = hop.inputarg(hop.args_r[0], 0)
        return hop.llops.convertvar(v_obj, hop.args_r[0], hop.r_result)


class Entry(ExtRegistryEntry):
    _about_ = wrap

    s_result_annotation = annmodel.SomeObject()

    def specialize_call(self, hop):
        assert len(hop.args_r) == 1, 'wrap() takes exactly one argument'
        v_obj, = hop.inputargs(*hop.args_r)
        return hop.llops.convertvar(v_obj, hop.args_r[0], robject.pyobj_repr)

# _______________________________________________-
# the actual tests

# track __del__ calls
class DelMonitor(object):
    def __init__(self):
        self.reset()
    def reset(self):
        self.deletions = 0
    def notify(self):
        self.deletions += 1
    def report(self):
        return self.deletions

delmonitor = DelMonitor()

class DemoBaseNotExposed(object):
    """this is the doc string"""
    def __init__(self, a, b):
        self.a = a
        self.b = b
        if P:print 'init'

    def demo(self):
        """this is the doc for demo"""
        if P:print 'demo'
        return self.a + self.b


# a trivial class to be exposed
class DemoClass(DemoBaseNotExposed):
    def demonotcalled(self):
        return self.demo() + 42

    def __del__(self):
        delmonitor.notify()
        if P:print 'del'

    def __add__(self, other):
        # XXX I would like to use type(), but its support is very limited
        #return type(self)(self.a + other.a, self.b + other.b)
        return DemoClass(self.a + other.a, self.b + other.b)

# see if we get things exported with subclassing
class DemoSubclass(DemoClass):
    def __init__(self, a, b, c):
        #super(DemoSubclass, self).__init__(a, b)
        DemoClass.__init__(self, b, a)
        self.c = c

    def demo(self, *other):
        #if other: print other
        return float(DemoClass.demo(self))
    
    def otherdemo(self):
        return 'this is the DemoSubclass', self.a, self.b

    def __del__(self):
        pass # this is intentionally another thing

# see how classes are handled that were not annotated
class DemoNotAnnotated(object):
    def __init__(self):
        self.hugo = 42
    def retrieve(self):
        return self.hugo

def democlass_helper_sub(a, b):
    # prevend inlining
    if a == -42:
        return democlass_helper_sub(a-1, b)
    inst = DemoClass(a, b)
    pyobj = wrap(inst)
    obj = unwrap(pyobj, DemoClass)
    ret = obj.demo()
    inst = DemoSubclass(a, b, 42)
    pyobj = wrap(inst)
    obj = unwrap(pyobj, DemoSubclass)
    ret = obj.demo()
    return ret

def democlass_helper(a=int, b=int):
    delmonitor.reset()
    ret = democlass_helper_sub(a, b)
    return delmonitor.report(), ret, long(42)

def democlass_helper2(a=int, b=int):
    self = DemoClass(a, b)
    self.demo()
    self2 = DemoSubclass(a, b, 42)
    return self

# _______________________________________________
# creating our own setup function for the module

# this class *can* be used for faster access.
# the compiler anyway chews quite a bit on it...
class BuiltinHelper(object):
    # the following would be much easier if we had
    # loop unrolling right inside the flowing process
    src = []
    src.append('def __init__(self):')
    src.append('    import __builtin__ as b')
    import __builtin__
    for name in dir(__builtin__):
        obj = getattr(__builtin__, name)
        if callable(obj) and hasattr(obj, '__name__'):
            src.append('    self.%s = b.%s' % (name, obj.__name__))
    src = '\n'.join(src)
    #print src
    exec src
    del __builtin__, name, obj, src

def setup_new_module(mod, modname):
    # note the name clash with py.test on setup_module
    import types
    m = types.ModuleType(modname)
    allobjs = mod.__dict__.values()
    funcs = eval('[]') # or import list from __builtin__
    # one alternative
    #bltn = BuiltinHelper()
    # less code:
    import __builtin__ as bltn
    if P:print bltn.list('hallo')
    #from twisted.internet import reactor    
    #print dir(reactor)
    #whow this works
    isinstance = eval('isinstance')
    # above is possible, this is probably a better compromise:
    isinstance = bltn.isinstance
    for obj in allobjs:
        if isinstance(obj, types.BuiltinFunctionType):
            funcs.append( (obj.__name__, obj) )
    if P:print 'funcs=', funcs
    if P:print funcs[3:]
    #funcs += [2, 3, 5]
    # not yet
    stuff = bltn.range(10)
    if P:print stuff[3:]
    if P:print stuff[:3]
    if P:print stuff[3:7]
    if P:print stuff[:-1]
    funcs.sort()
    return m


# creating an object, wrapping, unwrapping, call function, check whether __del__ is called
def test_wrap_call_dtor():
    f = getcompiled(democlass_helper, use_boehm=not True, exports=[DemoSubclass])
    ret = f(2, 3)
    if P: print ret
    assert ret[0] == 1

# exposing and using classes from a generasted extension module
def test_expose_classes():
    m = get_compiled_module(democlass_helper2, use_boehm=not True, exports=[
        DemoClass, DemoSubclass, DemoNotAnnotated, setup_new_module])
    obj = m.DemoClass(2, 3)
    res = obj.demo()
    assert res == DemoClass(2, 3).demo()

def extfunc(inst):
    return inst.demo()

def extfunc2(tup):
    inst1, inst2 = tup
    return inst1.__add__(inst2)

def t(a=int, b=int, c=DemoClass):
    x = DemoClass(a, b)
    x.demo()
    DemoSubclass(a, a, b).demo()
    DemoSubclass(a, a, b).demo(6)
    y = DemoSubclass(a, a, b).demo(6, 'hu')
    extfunc(x)
    extfunc2( (x, x) )
    if isinstance(c, DemoSubclass):
        print 42
    return x.__add__(x), DemoBaseNotExposed(17, 4) # see if it works without wrapper

# exposing and using classes from a generasted extension module
def test_asd():
    m = get_compiled_module(t, use_boehm=not True, exports=[
        DemoClass, DemoSubclass, DemoNotAnnotated, extfunc, extfunc2])
    obj = m.DemoClass(2, 3)
    res = obj.demo()
    assert res == DemoClass(2, 3).demo()


if __name__=='__main__':
    test_expose_classes()
    
