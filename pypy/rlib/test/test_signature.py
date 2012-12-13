import py
from pypy.rlib.signature import signature, finishsigs
from pypy.rlib import types
from pypy.annotation import model
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.lltypesystem import rstr
from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy


def annotate_at(f, policy=None):
    t = TranslationContext()
    a = t.buildannotator(policy=policy)
    a.annotate_helper(f, [model.s_ImpossibleValue]*f.func_code.co_argcount, policy=policy)
    return a

def sigof(a, f):
    # returns [param1, param2, ..., ret]
    g = graphof(a.translator, f)
    return [a.bindings[v] for v in g.startblock.inputargs] + [a.bindings[g.getreturnvar()]]

def getsig(f, policy=None):
    a = annotate_at(f, policy=policy)
    return sigof(a, f)

def check_annotator_fails(caller):
    exc = py.test.raises(Exception, annotate_at, caller).value
    assert caller.func_name in repr(exc.args)


def test_bookkeeping():
    @signature('x', 'y', returns='z')
    def f(a, b):
        return a + len(b)
    f.foo = 'foo'
    assert f._signature_ == (('x', 'y'), 'z')
    assert f.func_name == 'f'
    assert f.foo == 'foo'
    assert f(1, 'hello') == 6

def test_basic():
    @signature(types.int(), types.str(), returns=types.char())
    def f(a, b):
        return b[a]
    assert getsig(f) == [model.SomeInteger(), model.SomeString(), model.SomeChar()]

def test_arg_errors():
    @signature(types.int(), types.str(), returns=types.int())
    def f(a, b):
        return a + len(b)
    @check_annotator_fails
    def ok_for_body(): # would give no error without signature
        f(2.0, 'b')
    @check_annotator_fails
    def bad_for_body(): # would give error inside 'f' body, instead errors at call
        f('a', 'b')

def test_return():
    @signature(returns=types.str())
    def f():
        return 'a'
    assert getsig(f) == [model.SomeString()]

    @signature(types.str(), returns=types.str())
    def f(x):
        return x
    def g():
        return f('a')
    a = annotate_at(g)
    assert sigof(a, f) == [model.SomeString(), model.SomeString()]

def test_return_errors():
    @check_annotator_fails
    @signature(returns=types.int())
    def int_not_char():
        return 'a'
    @check_annotator_fails
    @signature(types.str(), returns=types.int())
    def str_to_int(s):
        return s


def test_none():
    @signature(returns=types.none())
    def f():
        pass
    assert getsig(f) == [model.s_None]

def test_float():
    @signature(types.longfloat(), types.singlefloat(), returns=types.float())
    def f(a, b):
        return 3.0
    assert getsig(f) == [model.SomeLongFloat(), model.SomeSingleFloat(), model.SomeFloat()]

def test_basestring():
    @signature(types.basestring(), returns=types.int())
    def f(u):
        return len(u)
    assert getsig(f) == [model.SomeStringOrUnicode(), model.SomeInteger()]

def test_unicode():
    @signature(types.unicode(), returns=types.int())
    def f(u):
        return len(u)
    assert getsig(f) == [model.SomeUnicodeString(), model.SomeInteger()]


def test_ptr():
    policy = LowLevelAnnotatorPolicy()
    @signature(types.ptr(rstr.STR), returns=types.none())
    def f(buf):
        pass
    argtype = getsig(f, policy=policy)[0]
    assert isinstance(argtype, model.SomePtr)
    assert argtype.ll_ptrtype.TO == rstr.STR

    def g():
        f(rstr.mallocstr(10))
    getsig(g, policy=policy)


def test_list():
    @signature(types.list(types.int()), returns=types.int())
    def f(a):
        return len(a)
    argtype = getsig(f)[0]
    assert isinstance(argtype, model.SomeList)
    item = argtype.listdef.listitem
    assert item.s_value == model.SomeInteger()
    assert item.resized == True

    @check_annotator_fails
    def ok_for_body():
        f(['a'])
    @check_annotator_fails
    def bad_for_body():
        f('a')

    @signature(returns=types.list(types.char()))
    def ff():
        return ['a']
    @check_annotator_fails
    def mutate_broader():
        ff()[0] = 'abc'
    @check_annotator_fails
    def mutate_unrelated():
        ff()[0] = 1
    @check_annotator_fails
    @signature(types.list(types.char()), returns=types.int())
    def mutate_in_body(l):
        l[0] = 'abc'
        return len(l)

    def can_append():
        l = ff()
        l.append('b')
    getsig(can_append)

def test_array():
    @signature(returns=types.array(types.int()))
    def f():
        return [1]
    rettype = getsig(f)[0]
    assert isinstance(rettype, model.SomeList)
    item = rettype.listdef.listitem
    assert item.s_value == model.SomeInteger()
    assert item.resized == False

    def try_append():
        l = f()
        l.append(2)
    check_annotator_fails(try_append)

def test_dict():
    @signature(returns=types.dict(types.str(), types.int()))
    def f():
        return {'a': 1, 'b': 2}
    rettype = getsig(f)[0]
    assert isinstance(rettype, model.SomeDict)
    assert rettype.dictdef.dictkey.s_value   == model.SomeString()
    assert rettype.dictdef.dictvalue.s_value == model.SomeInteger()


def test_instance():
    class C1(object):
        pass
    class C2(C1):
        pass
    class C3(C2):
        pass
    @signature(types.instance(C3), returns=types.instance(C2))
    def f(x):
        assert isinstance(x, C2)
        return x
    argtype, rettype = getsig(f)
    assert isinstance(argtype, model.SomeInstance)
    assert argtype.classdef.classdesc.pyobj == C3
    assert isinstance(rettype, model.SomeInstance)
    assert rettype.classdef.classdesc.pyobj == C2

    @check_annotator_fails
    def ok_for_body():
        f(C2())
    @check_annotator_fails
    def bad_for_body():
        f(C1())

def test_self():
    @finishsigs
    class C(object):
        @signature(types.self(), types.self(), returns=types.none())
        def f(self, other):
            pass
    class D1(C):
        pass
    class D2(C):
        pass

    def g():
        D1().f(D2())
    a = annotate_at(g)

    argtype = sigof(a, C.__dict__['f'])[0]
    assert isinstance(argtype, model.SomeInstance)
    assert argtype.classdef.classdesc.pyobj == C

def test_self_error():
    class C(object):
        @signature(types.self(), returns=types.none())
        def incomplete_sig_meth(self):
            pass

    exc = py.test.raises(Exception, annotate_at, C.incomplete_sig_meth).value
    assert 'incomplete_sig_meth' in repr(exc.args)
    assert 'finishsigs' in repr(exc.args)
