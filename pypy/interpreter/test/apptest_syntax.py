def test_condexpr():
    for s, expected in [("x = 1 if True else 2", 1),
                        ("x = 1 if False else 2", 2)]:
        exec s
        assert x == expected

def test_condexpr_no_warning():
    import warnings

    warnings.simplefilter('error', SyntaxWarning)
    exec "1 if True else 2"
    warnings.simplefilter('default', SyntaxWarning)

def test_bare_yield():
    s = "def f():\n    yield"

    exec s

def test_function_decorators():
    def other():
        return 4
    def dec(f):
        return other
    ns = {}
    ns["dec"] = dec
    exec """@dec
def g():
    pass""" in ns
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
    exec """@dec1
@dec2
def g(): pass""" in ns
    assert record == [2, 1]
    del record[:]
    exec """@dec1
@dec2
class x: pass""" in ns
    assert record == [2, 1]

def test_class_decorators():
    s = """@func
class x: pass"""
    ns = {"func" : lambda cls: 4}
    exec s in ns
    assert ns["x"] == 4

def test_simple_print():
    import __builtin__
    s = """from __future__ import print_function
x = print
"""
    ns = {}
    exec s in ns
    assert ns["x"] is getattr(__builtin__, "print")

def test_print():
    s = """from __future__ import print_function
import StringIO
s = StringIO.StringIO()
print("Hello,", "person", file=s)
"""
    ns = {}
    exec s in ns
    assert ns["s"].getvalue() == "Hello, person\n"

def test_simple():
    s = """from __future__ import unicode_literals
x = 'u'
y = r'u'
z = u'u'
b = b'u'
c = br'u'"""
    ns = {}
    exec s in ns
    assert isinstance(ns["x"], unicode)
    assert isinstance(ns["y"], unicode)
    assert isinstance(ns["z"], unicode)
    assert isinstance(ns["b"], str)
    assert isinstance(ns["c"], str)

def test_both_futures_with_semicolon():
    # Issue #2526: a corner case which crashes only if the file
    # contains *nothing more* than two __future__ imports separated
    # by a semicolon.
    s = """
from __future__ import unicode_literals; from __future__ import print_function
"""
    exec s in {}

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
        exec "with = 9"

def test_with_as_keyword_compound():
    with raises(SyntaxError):
        exec "from __future__ import generators, with_statement\nwith = 9"

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
            exec snippet
