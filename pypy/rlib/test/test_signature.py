import py
from pypy.rlib.signature import signature
from pypy.annotation import types, model
from pypy.translator.translator import TranslationContext, graphof


def annotate_at(f):
    t = TranslationContext()
    a = t.buildannotator()
    a.annotate_helper(f, [model.s_ImpossibleValue]*f.func_code.co_argcount)
    return a

def sigof(a, f):
    # returns [param1, param2, ..., ret]
    g = graphof(a.translator, f)
    return [a.bindings[v] for v in g.startblock.inputargs] + [a.bindings[g.getreturnvar()]]

def getsig(f):
    a = annotate_at(f)
    return sigof(a, f)

def check_annotator_fails(caller):
    exc = py.test.raises(Exception, annotate_at, caller).value
    assert caller.func_name in repr(exc.args)


def test_signature_bookkeeping():
    @signature('x', 'y', returns='z')
    def f(a, b):
        return a + len(b)
    f.foo = 'foo'
    assert f._signature_ == (('x', 'y'), 'z')
    assert f.func_name == 'f'
    assert f.foo == 'foo'
    assert f(1, 'hello') == 6

def test_signature_basic():
    @signature(types.int(), types.str(), returns=types.char())
    def f(a, b):
        return b[a]
    assert getsig(f) == [model.SomeInteger(), model.SomeString(), model.SomeChar()]

def test_signature_arg_errors():
    @signature(types.int(), types.str(), returns=types.int())
    def f(a, b):
        return a + len(b)
    @check_annotator_fails
    def ok_for_body(): # would give no error without signature
        f(2.0, 'b')
    @check_annotator_fails
    def bad_for_body(): # would give error inside 'f' body, instead errors at call
        f('a', 'b')

def test_signature_return():
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

def test_signature_return_errors():
    @check_annotator_fails
    @signature(returns=types.int())
    def int_not_char():
        return 'a'
    @check_annotator_fails
    @signature(types.str(), returns=types.int())
    def str_to_int(s):
        return s

def test_signature_list():
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

def test_signature_array():
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
