from __future__ import with_statement

def test_condexpr():
    for s, expected in [("x = 1 if True else 2", 1),
                        ("x = 1 if False else 2", 2)]:
        ns = {}
        exec(s, ns)
        assert ns['x'] == expected

def test_bare_yield():
    def f():
        yield

def test_function_decorators():
    def other():
        return 4
    def dec(f):
        return other
    ns = {}
    ns["dec"] = dec
    exec("""if 1:
                @dec
                def g():
                    pass
         """, ns)
    assert ns["g"] is other
    assert ns["g"]() == 4

def test_application_order():
    def dec1(f):
        record.append(1)
        return f
    def dec2(f):
        record.append(2)
        return f
    record = []
    ns = {"dec1" : dec1, "dec2" : dec2}
    exec("""if 1:
                @dec1
                @dec2
                def g():
                    pass
         """, ns)
    assert record == [2, 1]
    del record[:]
    exec("""if 1:
                @dec1
                @dec2
                class x:
                    pass
         """, ns)
    assert record == [2, 1]

def test_class_decorators():
    func = lambda cls: 4
    @func
    class x:
        pass
    assert x == 4

def test_simple_print():
    import builtins
    x = print
    assert x is builtins.print

def test_print():
    from _io import StringIO
    s = StringIO()
    print("Hello,", "person", file=s)
    assert s.getvalue() == "Hello, person\n"

# UnicodeLiterals

def test_simple_literals():
    s = """
x = 'u'
y = r'u'
b = b'u'
c = br'u'
d = rb'u'
"""
    ns = {}
    exec(s, ns)
    assert isinstance(ns["x"], str)
    assert isinstance(ns["y"], str)
    assert isinstance(ns["b"], bytes)
    assert isinstance(ns["c"], bytes)
    assert isinstance(ns["d"], bytes)

def test_triple_quotes():
    s = '''
x = """u"""
y = r"""u"""
b = b"""u"""
c = br"""u"""
d = rb"""u"""
'''

    ns = {}
    exec(s, ns)
    assert isinstance(ns["x"], str)
    assert isinstance(ns["y"], str)
    assert isinstance(ns["b"], bytes)
    assert isinstance(ns["c"], bytes)
    assert isinstance(ns["d"], bytes)

def test_both_futures_with_semicolon():
    # Issue #2526: a corner case which crashes only if the file
    # contains *nothing more* than two __future__ imports separated
    # by a semicolon.
    s = """
from __future__ import unicode_literals; from __future__ import print_function
"""
    exec(s, {})

# Comprehensions

def test_dictcomps():
    d = eval("{x : x for x in range(10)}")
    assert isinstance(d, dict)
    assert d == dict(zip(range(10), range(10)))
    d = eval("{x : x for x in range(10) if x % 2}")
    l = [x for x in range(10) if x % 2]
    assert d == dict(zip(l, l))

def test_setcomps():
    s = eval("{x for x in range(10)}")
    assert isinstance(s, set)
    assert s == set(range(10))
    s = eval("{x for x in range(10) if x % 2}")
    assert s == set(x for x in range(10) if x % 2)

def test_set_literal():
    s = eval("{1}")
    assert isinstance(s, set)
    assert s == set((1,))
    s = eval("{0, 1, 2, 3}")
    assert isinstance(s, set)
    assert s == set(range(4))

# With
def test_with_simple():
    class Context:
        def __init__(self):
            self.calls = list()

        def __enter__(self):
            self.calls.append('__enter__')

        def __exit__(self, exc_type, exc_value, exc_tb):
            self.calls.append('__exit__')

    acontext = Context()
    with acontext:
        pass
    assert acontext.calls == '__enter__ __exit__'.split()

def test_compound_with():
    class Context:
        def __init__(self, var):
            self.record = []
            self.var = var
        def __enter__(self):
            self.record.append(("__enter__", self.var))
            return self.var
        def __exit__(self, tp, value, tb):
            self.record.append(("__exit__", self.var))
    c1 = Context("blah")
    c2 = Context("bling")
    with c1 as v1, c2 as v2:
        pass
    assert v1 == "blah"
    assert v2 == "bling"
    assert c1.record == [("__enter__", "blah"), ("__exit__", "blah")]
    assert c2.record == [("__enter__", "bling"), ("__exit__", "bling")]

def test_with_as_var():
    class Context:
        def __init__(self):
            self.calls = list()

        def __enter__(self):
            self.calls.append('__enter__')
            return self.calls

        def __exit__(self, exc_type, exc_value, exc_tb):
            self.calls.append('__exit__')
            self.exit_params = (exc_type, exc_value, exc_tb)

    acontextfact = Context()
    with acontextfact as avar:
        avar.append('__body__')
        pass
    assert acontextfact.exit_params == (None, None, None)
    assert acontextfact.calls == '__enter__ __body__ __exit__'.split()

def test_with_raise_exception():
    class Context:
        def __init__(self):
            self.calls = list()

        def __enter__(self):
            self.calls.append('__enter__')
            return self.calls

        def __exit__(self, exc_type, exc_value, exc_tb):
            self.calls.append('__exit__')
            self.exit_params = (exc_type, exc_value, exc_tb)

    acontextfact = Context()
    error = RuntimeError('With Test')
    try:
        with acontextfact as avar:
            avar.append('__body__')
            raise error
            avar.append('__after_raise__')
    except RuntimeError:
        pass
    else:
        raise AssertionError('With did not raise RuntimeError')
    assert acontextfact.calls == '__enter__ __body__ __exit__'.split()
    assert acontextfact.exit_params[0:2] == (RuntimeError, error)
    import types
    assert isinstance(acontextfact.exit_params[2], types.TracebackType)

def test_with_swallow_exception():
    class Context:
        def __init__(self):
            self.calls = list()

        def __enter__(self):
            self.calls.append('__enter__')
            return self.calls

        def __exit__(self, exc_type, exc_value, exc_tb):
            self.calls.append('__exit__')
            self.exit_params = (exc_type, exc_value, exc_tb)
            return True

    acontextfact = Context()
    error = RuntimeError('With Test')
    with acontextfact as avar:
        avar.append('__body__')
        raise error
        avar.append('__after_raise__')
    assert acontextfact.calls == '__enter__ __body__ __exit__'.split()
    assert acontextfact.exit_params[0:2] == (RuntimeError, error)
    import types
    assert isinstance(acontextfact.exit_params[2], types.TracebackType)

def test_with_reraise_exception():
    class Context:
        def __enter__(self):
            self.calls = []
        def __exit__(self, exc_type, exc_value, exc_tb):
            self.calls.append('exit')
            raise

    c = Context()
    try:
        with c:
            1 / 0
    except ZeroDivisionError:
        pass
    else:
        raise AssertionError('Should have reraised initial exception')
    assert c.calls == ['exit']

def test_with_break():
    class Context:
        def __init__(self):
            self.calls = list()

        def __enter__(self):
            self.calls.append('__enter__')
            return self.calls

        def __exit__(self, exc_type, exc_value, exc_tb):
            self.calls.append('__exit__')
            self.exit_params = (exc_type, exc_value, exc_tb)

    acontextfact = Context()
    error = RuntimeError('With Test')
    for x in 1,:
        with acontextfact as avar:
            avar.append('__body__')
            break
            avar.append('__after_break__')
    else:
        raise AssertionError('Break failed with With, reached else clause')
    assert acontextfact.calls == '__enter__ __body__ __exit__'.split()
    assert acontextfact.exit_params == (None, None, None)

def test_with_continue():
    class Context:
        def __init__(self):
            self.calls = list()

        def __enter__(self):
            self.calls.append('__enter__')
            return self.calls

        def __exit__(self, exc_type, exc_value, exc_tb):
            self.calls.append('__exit__')
            self.exit_params = (exc_type, exc_value, exc_tb)

    acontextfact = Context()
    error = RuntimeError('With Test')
    for x in 1,:
        with acontextfact as avar:
            avar.append('__body__')
            continue
            avar.append('__after_continue__')
    else:
        avar.append('__continue__')
    assert acontextfact.calls == '__enter__ __body__ __exit__ __continue__'.split()
    assert acontextfact.exit_params == (None, None, None)

def test_with_return():
    class Context:
        def __init__(self):
            self.calls = list()

        def __enter__(self):
            self.calls.append('__enter__')
            return self.calls

        def __exit__(self, exc_type, exc_value, exc_tb):
            self.calls.append('__exit__')
            self.exit_params = (exc_type, exc_value, exc_tb)

    acontextfact = Context()
    error = RuntimeError('With Test')
    def g(acontextfact):
        with acontextfact as avar:
            avar.append('__body__')
            return '__return__'
            avar.append('__after_return__')
    acontextfact.calls.append(g(acontextfact))
    assert acontextfact.calls == '__enter__ __body__ __exit__ __return__'.split()
    assert acontextfact.exit_params == (None, None, None)

def test_with_as_keyword():
    with raises(SyntaxError):
        exec("with = 9")

def test_with_as_keyword_compound():
    with raises(SyntaxError):
        exec("from __future__ import generators, with_statement\nwith = 9")

def test_missing_as_SyntaxError():
    snippets = [
        "import os.path a bar ",
        "from os import path a bar",
        """
with foo a bar:
pass
"""]
    for snippet in snippets:
        with raises(SyntaxError):
            exec(snippet)

# FunctionAnnotations

def test_simple_annotation():
    def f(e:3=4): pass
    assert f.__annotations__ == {"e" : 3}
    def f(a : 1, b : 2, *var : 3, hi : 4, bye : 5=0, **kw : 6) -> 42: pass
    assert f.__annotations__ == {"a" : 1, "b" : 2, "var" : 3, "hi" : 4,
                                "bye" : 5, "kw" : 6, "return" : 42}

def test_bug_annotations_lambda():
    # those used to crash
    def broken(*a: lambda x: None):
        pass

    def broken(**a: lambda x: None):
        pass

def test_bug_annotation_inside_nested_function():
    # this used to crash
    def f1():
        def f2(*args: int):
            pass
    f1()

# SyntaxError

def test_tokenizer_error_location():
    line4 = "if ?: pass\n"
    try:
        exec("print\nprint\nprint\n" + line4)
    except SyntaxError as e:
        assert e.lineno == 4
        assert e.text == line4
        assert e.offset == e.text.index('?') + 1
    else:
        raise Exception("no SyntaxError??")

def test_grammar_error_location():
    try:
        exec("""if 1:
            class Foo:
                bla
                a as e
                bar
        """)
    except SyntaxError as e:
        assert e.lineno == 4
        assert e.text.endswith('a as e\n')
        print(e.offset, e.text.index('as'))
        assert e.offset == e.text.index('as') + 1 # offset is 1-based
    else:
        raise Exception("no SyntaxError??")

def test_astbuilder_error_location():
    program = "(1, 2) += (3, 4)\n"
    try:
        exec(program)
    except SyntaxError as e:
        assert e.lineno == 1
        assert e.text == program
    else:
        raise Exception("no SyntaxError??")

def test_codegen_error_location():
    try:
        exec("if 1:\n     break")
    except SyntaxError as e:
        assert e.lineno == 2
        assert "'break'" in e.msg
        assert e.filename == "<string>"
        assert e.offset == 6

def test_exception_target_in_nested_scope():
    # issue 4617: This used to raise a SyntaxError
    # "can not delete variable 'e' referenced in nested scope"
    def print_error():
        e
    try:
        something
    except Exception as e:
        print_error()
        # implicit "del e" here

def test_cpython_issue2382():
    code = 'Python = "\u1e54\xfd\u0163\u0125\xf2\xf1" +'
    exc = raises(SyntaxError, compile, code, 'foo', 'exec')
    assert exc.value.offset in (19, 20) # pypy, cpython

def test_empty_tuple_target():
    def f(n):
        () = ()
        ((), ()) = [[], []]
        del ()
        del ((), ())
        [] = {}
        ([], ()) = [[], ()]
        [[], ()] = ((), [])
        del []
        del [[], ()]
        for () in [(), []]: pass
        for [] in ([],): pass
        class Zen:
            def __enter__(self): return ()
            def __exit__(self, *args): pass
        with Zen() as (): pass
        () = [2, 3] * n
    f(0)
    try:
        f(5)
    except ValueError:
        pass
    else:
        raise AssertionError("should have raised")

def test_starunpacking_as_iterator():
    l = []
    a = [1, 2, 3, 4]
    b = [6, 7]
    c = ()
    for x in *a, *b, *c:
        l.append(x)
    assert l == [1, 2, 3, 4, 6, 7]
