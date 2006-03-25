from pypy.translator.translator import TranslationContext
from pypy import conftest
from py.test import raises
from pypy.rpython import extregistry
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import instantiate

P = False  # debug printing

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
                use_boehm=False, exports=[]):
    from pypy.translator.translator import TranslationContext
    from pypy.translator.backendopt.all import backend_optimizations

    from pypy.translator.c import gc
    from pypy.translator.c.genc import CExtModuleBuilder

    global t # allow us to view later
    t = TranslationContext()
    do_register(t)
    t.buildannotator().build_types(func, get_annotation(func))
    if view:
        t.viewcg()
    rtyper = t.buildrtyper()
    bk = rtyper.annotator.bookkeeper
    instantiators = {}
    for obj in exports:
        if isinstance(obj, type):
            cls = obj
            def make():
                return instantiate(cls)
            make.__name__ = cls.__name__ + '__new__'
            t.annotator.build_types(make, [])
            instantiators[cls] = make
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
    db = cbuilder.build_database(exports=exports, instantiators=instantiators)
    cbuilder.generate_source(db)
    cbuilder.compile()

    if view:
        t.viewcg()
    return cbuilder.import_module()

def getcompiled(func, *args, **kwds):
    module = get_compiled_module(func, *args, **kwds)
    return getattr(module, func.__name__)

# _______________________________________________-
# stubs for special annotation/rtyping


def create_pywrapper(thing):
    RaiseNameError

def unwrap_obj(pyobj, typ):
    RaiseNameError

def call_destructor(thing):
    ll_call_destructor(thing)

def ll_call_destructor(thang):
    return 42 # really not relevant

"""
creating a wrapper object with its destructor.
Note that we need annotate_helper_fn, because
the destructor is never explicitly called.
"""

def rtype_wrap_object(hop):
    v_any, = hop.inputargs(*hop.args_r)
    f = call_destructor
    hop.genop('gc_protect', [v_any])
    ARGTYPE = hop.args_r[0].lowleveltype
    FUNCTYPE = lltype.FuncType([ARGTYPE], lltype.Void)
    fp_dtor = hop.rtyper.annotate_helper_fn(f, [ARGTYPE])
    c_dtor = hop.inputconst(lltype.Ptr(FUNCTYPE), fp_dtor)
    return hop.llops.gencapicall('PyCObject_FromVoidPtr', [v_any, c_dtor],
                     resulttype=hop.r_result)

def rtype_destruct_object(hop):
    v_any, = hop.inputargs(hop.args_r[0])
    hop.genop('gc_unprotect', [v_any])

def rtype_unwrap_object(hop):
    v_pyobj, v_type = hop.inputargs(*hop.args_r)
    v_adr = hop.llops.gencapicall('PyCObject_AsVoidPtr', [v_pyobj],
                                  resulttype=hop.r_result)
    hop.genop('gc_protect', [v_adr])
    return v_adr

"""
The following registers the new mappings. The registration
had to be done from a function, because we need to pass the
translator in.

Note that these registrations are for explicit wrapping/unwrapping
which was the first thing I tried. Meanwhile similar functionality
has been added to rclass.py to support automatic wrapping.
"""

def do_register(t):
    def compute_annotation_unwrap(s_wrapper, s_class_or_inst):
        if hasattr(s_class_or_inst, 'classdef'):
            classdef = s_class_or_inst.classdef
        else:
            classdef = t.annotator.bookkeeper.getuniqueclassdef(s_class_or_inst.const)
        return annmodel.SomeInstance(classdef)

    extregistry.register_value(create_pywrapper, 
        compute_result_annotation=annmodel.SomeObject(), 
        specialize_call=rtype_wrap_object)
        
    extregistry.register_value(ll_call_destructor, 
        compute_result_annotation=lambda *args:None,
        specialize_call=rtype_destruct_object)

    extregistry.register_value(unwrap_obj, 
        compute_result_annotation=compute_annotation_unwrap,
        specialize_call=rtype_unwrap_object)

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

# a trivial class to be exposed
class DemoClass(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
        if P:print 'init'

    def demo(self):
        if P:print 'demo'
        return self.a + self.b

    def demonotcalled(self):
        return self.demo() + 42

    def __del__(self):
        delmonitor.notify()
        if P:print 'del'

# see if we get things exported with subclassing
class DemoSubclass(DemoClass):
    def demo(self):
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

# we have more helper functions here than needed.
# this was to make the debugging easier.

def call_create_pywrapper(inst):
    return create_pywrapper(inst)
    # this could work, but we need to loose ref.
    # also: how to generically know if we have the attribute?
    if inst._wrapper:
        return inst._wrapper
    inst._wrapper = create_pywrapper(inst)
    return inst._wrapper

def call_unwrap_obj(pyobj, klass):
    return unwrap_obj(pyobj, klass)

def democlass_helper_sub(a, b):
    # prevend inlining
    if a == -42:
        return democlass_helper_sub(a-1, b)
    inst = DemoClass(a, b)
    pyobj = call_create_pywrapper(inst)
    obj = call_unwrap_obj(pyobj, DemoClass)
    ret = obj.demo()
    return ret

def democlass_helper(a=int, b=int):
    delmonitor.reset()
    ret = democlass_helper_sub(a, b)
    return delmonitor.report(), ret, 42 # long(42) # this creates ATM a bad crash

def democlass_helper2(a=int, b=int):
    self = DemoClass(a, b)
    self.demo()
    self2 = DemoSubclass(a, b)
    return self

# creating an object, wrapping, unwrapping, call function, check whether __del__ is called
def test_wrap_call_dtor():
    f = getcompiled(democlass_helper, use_boehm=not True)
    ret = f(2, 3)
    if P: print ret
    assert ret[0] == 1

# exposing and using classes from a generasted extension module
def test_expose_classes():
    m = get_compiled_module(democlass_helper2, use_boehm=not True, exports=[
        DemoClass, DemoSubclass, DemoNotAnnotated])
    obj = m.DemoClass(2, 3)
    res = obj.demo()
    assert res == DemoClass(2, 3).demo()
