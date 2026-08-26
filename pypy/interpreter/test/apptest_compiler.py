# encoding: utf-8
import sys
from pytest import raises, skip

IS_PYPY = "__pypy__" in sys.builtin_module_names


def test_bom_with_future():
    s = b'\xef\xbb\xbffrom __future__ import division\nx = 1/2'
    ns = {}
    exec(s, ns)
    assert ns["x"] == .5

def test_noop_future_import():
    code1 = compile("from __future__ import division", "<test>", "exec")
    code2 = compile("", "<test>", "exec")
    assert code1.co_flags == code2.co_flags

def test_values_of_different_types():
    ns = {}
    exec("a = 0; c = 0.0; d = 0j", ns)
    assert type(ns['a']) is int
    assert type(ns['c']) is float
    assert type(ns['d']) is complex

def test_values_of_different_types_in_tuples():
    ns = {}
    exec("a = ((0,),); c = ((0.0,),); d = ((0j,),)", ns)
    assert type(ns['a'][0][0]) is int
    assert type(ns['c'][0][0]) is float
    assert type(ns['d'][0][0]) is complex

def test_zeros_not_mixed():
    import math, sys
    code = compile("x = -0.0; y = 0.0", "<test>", "exec")
    consts = code.co_consts
    if IS_PYPY:
        # Hard to test on CPython, since co_consts is randomly ordered
        x, y, z = consts
        assert isinstance(x, float) and isinstance(y, float)
        assert math.copysign(1, x) != math.copysign(1, y)
    ns = {}
    exec("z1, z2 = 0j, -0j", ns)
    assert math.atan2(ns["z1"].imag, -1.) == math.atan2(0., -1.)
    assert math.atan2(ns["z2"].imag, -1.) == math.atan2(-0., -1.)

def test_zeros_not_mixed_in_tuples():
    import math
    ns = {}
    exec("a = (0.0, 0.0); b = (-0.0, 0.0); c = (-0.0, -0.0)", ns)
    assert math.copysign(1., ns['a'][0]) == 1.0
    assert math.copysign(1., ns['a'][1]) == 1.0
    assert math.copysign(1., ns['b'][0]) == -1.0
    assert math.copysign(1., ns['b'][1]) == 1.0
    assert math.copysign(1., ns['c'][0]) == -1.0
    assert math.copysign(1., ns['c'][1]) == -1.0

def test_ellipsis_anywhere():
    x = ...
    assert x is Ellipsis

def test_keywordonly_syntax_errors():
    cases = ("def f(p, *):\n  pass\n",
             "def f(p1, *, p1=100):\n  pass\n",
             "def f(p1, *k1, k1=100):\n  pass\n",
             "def f(p1, *, k1, k1=100):\n  pass\n",
             "def f(p1, *, **k1):\n  pass\n",
             "def f(p1, *, k1, **k1):\n  pass\n",
             "def f(p1, *, None, **k1):\n  pass\n",
             "def f(p, *, (k1, k2), **kw):\n  pass\n")
    for case in cases:
        raises(SyntaxError, compile, case, "<test>", "exec")

def test_barry_as_bdfl():
    # from test_flufl.py :-)
    import __future__
    code = "from __future__ import barry_as_FLUFL; 2 {0} 3"
    compile(code.format('<>'), '<BDFL test>', 'exec',
            __future__.CO_FUTURE_BARRY_AS_BDFL)
    with raises(SyntaxError) as excinfo:
        compile(code.format('!='),
           '<FLUFL test>', 'exec',
           __future__.CO_FUTURE_BARRY_AS_BDFL)
    assert excinfo.value.msg == "with Barry as BDFL, use '<>' instead of '!='"

def test_guido_as_bdfl():
    # from test_flufl.py :-)
    code = '2 {0} 3'
    compile(code.format('!='), '<BDFL test>', 'exec')
    raises(SyntaxError, compile, code.format('<>'),
           '<FLUFL test>', 'exec')

def test_surrogate():
    s = '\udcff'
    raises(UnicodeEncodeError, compile, s, 'foo', 'exec')

def test_pep3131():
    # XXX: the 4th name is currently mishandled by narrow builds
    class T:
        ä = 1
        µ = 2 # this is a compatibility character
        蟒 = 3
        #x󠄀 = 4
    assert getattr(T, '\xe4') == 1
    assert getattr(T, 'μ') == 2
    assert getattr(T, '蟒') == 3
    #assert getattr(T, 'x\U000E0100') == 4
    expected = ("['__dict__', '__doc__', '__module__', '__weakref__', "
    #            "x󠄀", "'ä', 'μ', '蟒']")
                "'ä', 'μ', '蟒']")
    assert expected in str(sorted(T.__dict__.keys()))

def test_unicode_identifier():
    c = compile("# coding=latin-1\n\u00c6 = '\u00c6'", "dummy", "exec")
    d = {}
    exec(c, d)
    assert d['\xc6'] == '\xc6'
    c = compile("日本 = 8; 日本2 = 日本 + 1; del 日本;", "dummy", "exec")
    exec(c, d)
    assert '日本2' in d
    assert d['日本2'] == 9
    assert '日本' not in d

    raises(SyntaxError, eval, b'\xff\x20')
    raises(SyntaxError, eval, b'\xef\xbb\x20')

def test_unicode_identifier_error_offset():
    info = raises(SyntaxError, eval, b'\xe2\x82\xac = 1')
    assert info.value.offset == 1
    assert raises(SyntaxError, eval, b'\xc3\xa4 + \xe2\x82\xac').value.offset == 5

def test_import_nonascii():
    c = compile('from os import 日本', '', 'exec')
    assert ('日本',) in c.co_consts

def test_class_nonascii():
    class 日本:
        pass
    assert 日本.__name__ == '日本'
    assert 日本.__qualname__ == 'test_class_nonascii.<locals>.日本'
    assert '日本' in repr(日本)

def test_cpython_issue2301():
    try:
        compile(b"# coding: utf7\nprint '+XnQ-'", "dummy", "exec")
    except SyntaxError as v:
        assert v.text ==  "print '\u5e74'\n"
    else:
        assert False, "Expected SyntaxError"

def test_invalid_utf8():
    e = raises(SyntaxError, compile, b'\x80', "dummy", "exec")
    assert str(e.value).startswith('Non-UTF-8 code')
    assert 'but no encoding declared' in str(e.value)
    e = raises(SyntaxError, compile, b'# coding: utf-8\n\x80',
               "dummy", "exec")
    assert str(e.value).startswith('Non-UTF-8 code')
    assert 'but no encoding declared' not in str(e.value)

def test_invalid_utf8_in_comments_or_strings():
    import sys
    compile(b"# coding: latin1\n#\xfd\n", "dummy", "exec")
    raises(SyntaxError, compile, b"# coding: utf-8\n'\xfd'\n",
           "dummy", "exec") #1
    excinfo = raises(SyntaxError, compile, b'# coding: utf-8\nx=5\nb"\xfd"\n',
           "dummy", "exec") #2
    assert excinfo.value.lineno == 3
    # the following example still fails on CPython 3.5.2, skip if -A
    if IS_PYPY:
        raises(SyntaxError, compile, b"# coding: utf-8\n#\xfd\n",
               "dummy", "exec") #3

def test_invalid_utf8_in_multiline_string():
    # gh96611: non-UTF-8 byte inside a multiline string literal should
    # produce "Non-UTF-8 code starting with '\xNN'" not a codec error
    excinfo = raises(SyntaxError, compile, b'print("""\n\xb1""")\n',
                     "dummy", "exec")
    print(excinfo.value)
    assert str(excinfo.value).startswith("Non-UTF-8 code starting with '\\xb1'")

def test_cpython_issues_24022_25388():
    from _ast import PyCF_ACCEPT_NULL_BYTES
    raises(SyntaxError, compile, b'0000\x00\n00000000000\n\x00\n\x9e\n',
           "dummy", "exec", PyCF_ACCEPT_NULL_BYTES)
    raises(SyntaxError, compile, b"#\x00\n#\xfd\n", "dummy", "exec",
           PyCF_ACCEPT_NULL_BYTES)
    raises(SyntaxError, compile, b"#\x00\nx=5#\xfd\n", "dummy", "exec",
           PyCF_ACCEPT_NULL_BYTES)

def test_correct_offset_in_many_bytes():
    excinfo = raises(SyntaxError, compile, b'# coding: utf-8\nx = b"a" b"c" b"\xfd"\n',
           "dummy", "exec")
    assert excinfo.value.lineno == 2
    assert excinfo.value.offset == 17

def test_zeros_not_mixed_in_lambdas():
    import math
    code = compile("x = lambda: -0.0; y = lambda: 0.0", "<test>", "exec")
    consts = code.co_consts
    x, y, z = consts
    assert isinstance(x, type(code)) and isinstance(y, type(code))
    assert x is not y
    assert x != y

def test_dont_share_lambdas():
    if not IS_PYPY:
        skip("pypy-only optimization")
    # the two lambdas's codes aren't shared (CPython does that but it's
    # completely pointless: it only applies to identical lambdas that are
    # defined on the same line)
    code = compile("x = lambda: 0; y = lambda: 0", "<test>", "exec")
    consts = code.co_consts
    x, y, z = consts
    assert isinstance(x, type(code)) and isinstance(y, type(code))
    assert x is not y
    assert x == y

def test_dict_and_set_literal_order():
    x = 1
    l1 = list({1:'a', 3:'b', 2:'c', 4:'d'})
    l2 = list({1, 3, 2, 4})
    l3 = list({x:'a', 3:'b', 2:'c', 4:'d'})
    l4 = list({x, 3, 2, 4})
    if not IS_PYPY:
        # the full test relies on the host Python providing ordered dicts
        assert set(l1) == set(l2) == set(l3) == set(l4) == {1, 3, 2, 4}
    else:
        assert l1 == l2 == l3 == l4 == [1, 3, 2, 4]

def test_freevars_order():
    # co_cellvars and co_freevars are guaranteed to appear in
    # alphabetical order.  See CPython Issue #15368 (which does
    # not come with tests).
    source = """if 1:
    def f1(x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12,x13,x14,x15):
        def g1():
            return (x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12,x13,x14,x15)
        return g1
    def f2(x15,x14,x13,x12,x11,x10,x9,x8,x7,x6,x5,x4,x3,x2,x1):
        def g2():
            return (x15,x14,x13,x12,x11,x10,x9,x8,x7,x6,x5,x4,x3,x2,x1)
        return g2
    c1 = f1(*range(15)).__code__.co_freevars
    c2 = f2(*range(15)).__code__.co_freevars
    r1 = f1.__code__.co_cellvars
    r2 = f2.__code__.co_cellvars
    """
    d = {}
    exec(source, d)
    assert d['c1'] == d['c2']
    # the test above is important for a few bytecode hacks,
    # but actually we get them in alphabetical order, so check that:
    assert d['c1'] == tuple(sorted(d['c1']))
    assert d['r1'] == d['r2'] == d['c1']

def test_code_equality():
    import _ast
    sample_code = [
        ['<assign>', 'x = 5'],
        ['<ifblock>', """if True:\n    pass\n"""],
        ['<forblock>', """for n in [1, 2, 3]:\n    print(n)\n"""],
        ['<deffunc>', """def foo():\n    pass\nfoo()\n"""],
    ]

    for fname, code in sample_code:
        co1 = compile(code, '%s1' % fname, 'exec')
        ast = compile(code, '%s2' % fname, 'exec', _ast.PyCF_ONLY_AST)
        assert type(ast) == _ast.Module
        co2 = compile(ast, '%s3' % fname, 'exec')
        assert co1 == co2
        # the code object's filename comes from the second compilation step
        assert co2.co_filename == '%s3' % fname

def test_invalid_ast():
    import _ast
    delete = _ast.Delete([])
    delete.lineno = 0
    delete.col_offset = 0
    mod = _ast.Module([delete], [])
    exc = raises(ValueError, compile, mod, 'filename', 'exec')
    assert str(exc.value) == "empty targets on Delete"

def test_evaluate_argument_definition_order():
    lst = [1, 2, 3, 4]
    def f(a=lst.pop(), b=lst.pop(), *, c=lst.pop(), d=lst.pop()):
        return (a, b, c, d)
    assert f('a') == ('a', 3, 2, 1), repr(f('a'))
    assert f() == (4, 3, 2, 1), repr(f())
    #
    lst = [1, 2, 3, 4]
    f = lambda a=lst.pop(), b=lst.pop(), *, c=lst.pop(), d=lst.pop(): (
        a, b, c, d)
    assert f('a') == ('a', 3, 2, 1), repr(f('a'))
    assert f() == (4, 3, 2, 1), repr(f())

# the following couple of tests are from test_super.py in the stdlib

def test_classcell():
    test_class = None
    class Meta(type):
        def __new__(cls, name, bases, namespace):
            nonlocal test_class
            self = super().__new__(cls, name, bases, namespace)
            test_class = self.f()
            return self
    class A(metaclass=Meta):
        @staticmethod
        def f():
            return __class__
    assert test_class is A

def test_classcell_missing():
    # Some metaclasses may not pass the original namespace to type.__new__
    # We test that case here by forcibly deleting __classcell__
    class Meta(type):
        def __new__(cls, name, bases, namespace):
            namespace.pop('__classcell__', None)
            return super().__new__(cls, name, bases, namespace)

    with raises(RuntimeError):
        class WithClassRef(metaclass=Meta):
            def f(self):
                return __class__

def test_classcell_overwrite():
    # Overwriting __classcell__ with nonsense is explicitly prohibited
    class Meta(type):
        def __new__(cls, name, bases, namespace, cell):
            namespace['__classcell__'] = cell
            return super().__new__(cls, name, bases, namespace)

    raises(TypeError, '''if 1:
        class A(metaclass=Meta, cell=object()):
            pass
    ''')

def test_classcell_wrong_cell():
    # Pointing the cell reference at the wrong class is prohibited
    class Meta(type):
        def __new__(cls, name, bases, namespace):
            cls = super().__new__(cls, name, bases, namespace)
            B = type("B", (), namespace)
            return cls

    # works, no __class__
    class A(metaclass=Meta):
        pass

    raises(TypeError, '''if 1:
        class A(metaclass=Meta):
            def f(self):
                return __class__
    ''')

def test_class_mro():
    test_class = None

    class Meta(type):
        def mro(self):
            # self.f() doesn't work yet...
            self.__dict__["f"]()
            return super().mro()

    class A(metaclass=Meta):
        def f():
            nonlocal test_class
            test_class = __class__

    assert test_class is A

def test_remove_ending():
    source = """def f():
        return 3
"""
    ns = {}
    exec(source, ns)
    code = ns['f'].__code__
    import dis, sys
    from io import StringIO
    s = StringIO()
    so = sys.stdout
    sys.stdout = s
    try:
        dis.dis(code)
    finally:
        sys.stdout = so
    output = s.getvalue()
    assert output.count('LOAD_CONST') + output.count('RETURN_CONST') == 1

def test_constant_name():
    import opcode
    for name in "None", "True", "False":
        snip = "def f(): return " + name
        co = compile(snip, "<test>", "exec").co_consts[0]
        if IS_PYPY:  # This is a pypy optimization
            assert name not in co.co_names
        co = co.co_code
        op = co[0]
        assert op == opcode.opmap["RETURN_CONST"]

def test_and_or_folding():
    if not IS_PYPY:
        return # pypy-only
    def f1():
        return True or 1 + x
    assert len(f1.__code__.co_code) == 4 # load_const, return_value
    def f2():
        return 0 and 1 + x
    assert len(f2.__code__.co_code) == 4 # load_const, return_value
    def f3():
        return a or False or True or x
    assert len(f3.__code__.co_code) == 8 # load_global, jump, load_const, return_value
    def f4():
        return a and True and 0 and x
    assert len(f4.__code__.co_code) == 8 # load_global, jump, load_const, return_value

def test_tuple_constants():
    ns = {}
    exec("x = (1, 0); y = (1, 0)", ns)
    assert isinstance(ns["x"][0], int)
    assert isinstance(ns["y"][0], int)

def test_ellipsis_truth():
    co = compile("if ...: x + 3\nelse: x + 4", "<test>", "exec")
    assert 4 not in co.co_consts

def test_division_folding():
    def code(source):
        return compile(source, "<test>", "exec")
    co = code("x = 10//4")
    if not IS_PYPY:
        assert 2 in co.co_consts
    else:
        # PyPy is more precise
        assert len(co.co_consts) == 2
        assert co.co_consts[0] == 2
    co = code("x = 10/4")
    if not IS_PYPY:
        assert 2.5 in co.co_consts
    else:
        assert len(co.co_consts) == 2
        assert co.co_consts[0] == 2.5

def test_tuple_folding():
    co = compile("x = (1, 2, 3)", "<test>", "exec")
    if IS_PYPY:
        # PyPy is more precise
        assert co.co_consts == ((1, 2, 3), None)
    else:
        assert (1, 2, 3) in co.co_consts
        assert None in co.co_consts
    co = compile("x = ()", "<test>", "exec")
    if IS_PYPY:
        # CPython does not constant-fold the empty tuple
        assert set(co.co_consts) == set(((), None))

def test_unary_folding():
    def check_const(co, value):
        assert value in co.co_consts
        if IS_PYPY:
            # This is a pypy optimization
            assert co.co_consts[0] == value
    co = compile("x = -(3)", "<test>", "exec")
    check_const(co, -3)
    co = compile("x = ~3", "<test>", "exec")
    check_const(co, ~3)
    co = compile("x = +(-3)", "<test>", "exec")
    check_const(co, -3)
    co = compile("x = not None", "<test>", "exec")
    if IS_PYPY:
        # CPython does not have this optimization
        assert co.co_consts == (True, None)

def test_folding_of_binops_on_constants():
    def disassemble(func):
        from io import StringIO
        import sys, dis
        f = StringIO()
        tmp = sys.stdout
        sys.stdout = f
        dis.dis(func)
        sys.stdout = tmp
        result = f.getvalue()
        f.close()
        return result

    def dis_single(line):
        return disassemble(compile(line, '', 'single'))

    for line, elem in (
        ('a = 2+3+4', '(9)'),                   # chained fold
        ('"@"*4', "('@@@@')"),                  # check string ops
        ('a="abc" + "def"', "('abcdef')"),      # check string ops
        ('a = 3**4', '(81)'),                   # binary power
        ('a = 3*4', '(12)'),                    # binary multiply
        ('a = 13//4', '(3)'),                   # binary floor divide
        ('a = 14%4', '(2)'),                    # binary modulo
        ('a = 2+3', '(5)'),                     # binary add
        ('a = 13-4', '(9)'),                    # binary subtract
        ('a = (12,13)[1]', '(13)'),             # binary subscr
        ('a = 13 << 2', '(52)'),                # binary lshift
        ('a = 13 >> 2', '(3)'),                 # binary rshift
        ('a = 13 & 7', '(5)'),                  # binary and
        ('a = 13 ^ 7', '(10)'),                 # binary xor
        ('a = 13 | 7', '(15)'),                 # binary or
        ):
        asm = dis_single(line)
        print(asm)
        assert elem in asm, 'ELEMENT not in asm'
        assert 'BINARY_' not in asm, 'BINARY_in_asm'

    # Verify that unfoldables are skipped
    asm = dis_single('a=2+"b"')
    assert '(2)' in asm
    assert "('b')" in asm

    # Verify that large sequences do not result from folding
    asm = dis_single('a="x"*1000')
    assert '(1000)' in asm

def test_folding_of_binops_on_constants_crash():
    compile('()[...]', '', 'eval')
    # assert did not crash

def test_dis_stopcode():
    source = """def _f(a):
            print(a)
            return 1
        """
    ns = {}
    exec(source, ns)
    code = ns['_f'].__code__

    import sys, dis
    from io import StringIO
    s = StringIO()
    save_stdout = sys.stdout
    sys.stdout = s
    try:
        dis.dis(code)
    finally:
        sys.stdout = save_stdout
    output = s.getvalue()
    assert "STOP_CODE" not in output

def test_optimize_list_comp():
    source = """def _f(a):
        return [x for x in a if None]
    """
    ns = {}
    exec(source, ns)
    code = ns['_f'].__code__

    import sys, dis
    from io import StringIO
    s = StringIO()
    out = sys.stdout
    sys.stdout = s
    try:
        dis.dis(code)
    finally:
        sys.stdout = out
    output = s.getvalue()
    assert "LOAD_GLOBAL" not in output

def test_folding_of_list_constants():
    source = 'a in [1, 2, 3]'
    co = compile(source, '', 'exec')
    i = co.co_consts.index((1, 2, 3))
    assert i > -1
    assert isinstance(co.co_consts[i], tuple)

def test_folding_of_set_constants():
    source = 'a in {1, 2, 3}'
    co = compile(source, '', 'exec')
    i = co.co_consts.index(set([1, 2, 3]))
    assert i > -1
    assert isinstance(co.co_consts[i], frozenset)

def test_call_method_kwargs():
    if not IS_PYPY:
        skip("CALL_METHOD exists only on pypy")
    source = """def _f(a):
        return a.f(a=a)
    """
    ns = {}
    exec(source, ns)
    code = ns['_f'].__code__

    import sys, dis
    from io import StringIO
    s = StringIO()
    out = sys.stdout
    sys.stdout = s
    try:
        dis.dis(code)
    finally:
        sys.stdout = out
    output = s.getvalue()
    assert "CALL_METHOD" in output, output

def test_interned_strings():
    source = """x = ('foo_bar42', 5); y = 'foo_bar42'; z = x[0]"""
    ns = {}
    exec(source, ns)
    assert ns['y'] is ns['z']

def test_indentation_error():
    source = """if 1:
    x
     y
    """
    try:
        exec(source)
    except IndentationError:
        pass
    else:
        raise Exception("DID NOT RAISE")

def test_bad_oudent():
    source = """if 1:
      x
      y
     z
    """
    try:
        exec(source)
    except IndentationError as e:
        assert e.msg == 'unindent does not match any outer indentation level'
    else:
        raise Exception("DID NOT RAISE")

def test_outdentation_error_filename():
    source = """if 1:
     x
    y
    """
    try:
        exec(source)
    except IndentationError as e:
        assert e.filename == '<string>'
    else:
        raise Exception("DID NOT RAISE")

def test_taberror():
    source = """if 1:
    x
\ty
    """
    try:
        exec(source)
    except TabError as e:
        pass
    else:
        raise Exception("DID NOT RAISE")

def test_repr_vs_str():
    source1 = "x = (\n"
    source2 = "x = (\n\n"
    try:
        exec(source1)
    except SyntaxError as e:
        err1 = e
    else:
        raise Exception("DID NOT RAISE")
    try:
        exec(source2)
    except SyntaxError as e:
        err2 = e
    else:
        raise Exception("DID NOT RAISE")
    # str() is the same for both (CPython pins the reported line to the
    # opening bracket regardless of how much unclosed source follows), but
    # repr() differs because it also embeds the raw source text.
    assert repr(err1) != repr(err2)
    err3 = eval(repr(err1))
    assert str(err3) == str(err1)
    assert repr(err3) == repr(err1)

def test_surrogate_filename():
    fname = '\udcff'
    co = compile("'dr cannon'", fname, 'exec')
    assert co.co_filename == fname
    try:
        compile("'dr", fname, 'exec')
    except SyntaxError as e:
        assert e.filename == fname
    else:
        assert False, 'SyntaxError expected'

def test_encoding():
    code = b'# -*- coding: badencoding -*-\npass\n'
    raises(SyntaxError, compile, code, 'tmp', 'exec')
    code = 'u"\xc2\xa4"\n'
    assert eval(code) == u'\xc2\xa4'
    code = u'u"\xc2\xa4"\n'
    assert eval(code) == u'\xc2\xa4'
    code = b'# -*- coding: latin1 -*-\nu"\xc2\xa4"\n'
    assert eval(code) == u'\xc2\xa4'
    code = b'# -*- coding: utf-8 -*-\nu"\xc2\xa4"\n'
    assert eval(code) == u'\xa4'
    code = b'# -*- coding: iso8859-15 -*-\nu"\xc2\xa4"\n'
    assert eval(code) == u'\xc2\u20ac'
    code = b'u"""\\\n# -*- coding: ascii -*-\n\xc2\xa4"""\n'
    assert eval(code) == u'# -*- coding: ascii -*-\n\xa4'

def test_asterror_has_line_without_file():
    code = u"print(1)\na/2 = 5\n"
    with raises(SyntaxError) as excinfo:
        compile(code, 'not a file!', 'exec')
    assert excinfo.value.text == "a/2 = 5\n"

def test_scope_unoptimized_clash1():
    # mostly taken from test_scope.py
    raises(SyntaxError, compile, """if 1:
        def unoptimized_clash1(strip):
            def f(s):
                from string import *
                return strip(s) # ambiguity: free or local
            return f""", '', 'exec')

def test_scope_unoptimized_clash1_b():
    # as far as I can tell, this case can be handled correctly
    # by the interpreter so a SyntaxError is not required, but
    # let's give one anyway for "compatibility"...

    # mostly taken from test_scope.py
    raises(SyntaxError, compile, """if 1:
        def unoptimized_clash1(strip):
            def f():
                from string import *
                return s # ambiguity: free or local (? no, global or local)
            return f""", '', 'exec')

def test_scope_exec_in_nested():
    raises(SyntaxError, compile, """if 1:
        def unoptimized_clash1(x):
            def f():
                exec "z=3"
                return x
            return f""", '', 'exec')

def test_scope_exec_with_nested_free():
    raises(SyntaxError, compile, """if 1:
        def unoptimized_clash1(x):
            exec "z=3"
            def f():
                return x
            return f""", '', 'exec')

def test_scope_importstar_in_nested():
    raises(SyntaxError, compile, """if 1:
        def unoptimized_clash1(x):
            def f():
                from string import *
                return x
            return f""", '', 'exec')

def test_scope_importstar_with_nested_free():
    raises(SyntaxError, compile, """if 1:
        def clash(x):
            from string import *
            def f(s):
                return strip(s)
            return f""", '', 'exec')

def test_try_except_finally():
    compile("""
def f():
    try:
       1/0
    except ZeroDivisionError:
       pass
    finally:
       return 3
""", '', 'exec')
    compile("""
def f():
    try:
        1/0
    except:
        pass
    else:
        pass
    finally:
        return 2
""", '', 'exec')

def test_toplevel_docstring():
    glob = {}
    loc = {}
    exec(compile('"spam"; "bar"; x=5', '<hello>', 'exec'), glob, loc)
    assert loc['x'] == 5
    assert loc['__doc__'] == "spam"
    #
    glob = {}
    loc = {}
    exec(compile('"spam"; "bar"; x=5', '<hello>', 'single'), glob, loc)
    assert loc['x'] == 5
    assert loc.get('__doc__') is None   # "spam" is not a docstring

def test_barestringstmts_disappear():
    code = compile('"a"\n"b"\n"c"\n', '<hello>', 'exec')
    # "a" should show up as a docstring, but "b" and "c" should not
    assert "b" not in code.co_consts
    assert "c" not in code.co_consts

def test_unicodeliterals():
    raises(SyntaxError, eval, "u'\\Ufffffffe'")
    raises(SyntaxError, eval, "u'\\Uffffffff'")
    raises(SyntaxError, eval, "u'\\U%08x'" % 0x110000)

def test_unicode_docstring():
    code = compile('"hello"\n', '<hello>', 'exec')
    assert code.co_consts[0] == "hello"
    assert type(code.co_consts[0]) is str

def test_argument_handling():
    for expr in 'lambda a,a:0', 'lambda a,a=1:0', 'lambda a=1,a=1:0':
        raises(SyntaxError, eval, expr)

    for code in ('def f(a, a): pass', 'def f(a = 0, a = 1): pass',
                 'def f(a): global a; a = 1'):
        raises(SyntaxError, compile, code, '', 'exec')

def test_argument_order():
    code = 'def f(a=1, (b, c)): pass'
    raises(SyntaxError, compile, code, '', 'exec')

def test_debug_assignment():
    code = '__debug__ = 1'
    raises(SyntaxError, compile, code, '', 'single')

def test_return_in_generator():
    code = 'def f():\n return None\n yield 19\n'
    compile(code, '', 'single')

def test_yield_in_finally():
    code ='def f():\n try:\n  yield 19\n finally:\n  pass\n'
    compile(code, '', 'single')

def test_none_assignment():
    stmts = [
        'None = 0',
        'None += 0',
        '__builtins__.None = 0',
        'def None(): pass',
        'class None: pass',
        '(a, None) = 0, 0',
        'for None in range(10): pass',
        'def f(None): pass',
    ]
    for stmt in stmts:
        stmt += '\n'
        for kind in 'single', 'exec':
            raises(SyntaxError, compile, stmt, '', kind)

def test_import():
    succeed = [
        'import sys',
        'import os, sys',
        'from __future__ import nested_scopes, generators',
        'from __future__ import (nested_scopes,\ngenerators)',
        'from __future__ import (nested_scopes,\ngenerators,)',
        'from __future__ import (\nnested_scopes,\ngenerators)',
        'from __future__ import(\n\tnested_scopes,\n\tgenerators)',
        'from __future__ import(\n\t\nnested_scopes)',
        'from sys import stdin, stderr, stdout',
        'from sys import (stdin, stderr,\nstdout)',
        'from sys import (stdin, stderr,\nstdout,)',
        'from sys import (stdin\n, stderr, stdout)',
        'from sys import (stdin\n, stderr, stdout,)',
        'from sys import stdin as si, stdout as so, stderr as se',
        'from sys import (stdin as si, stdout as so, stderr as se)',
        'from sys import (stdin as si, stdout as so, stderr as se,)',
        ]
    fail = [
        'import (os, sys)',
        'import (os), (sys)',
        'import ((os), (sys))',
        'import (sys',
        'import sys)',
        'import (os,)',
        'from (sys) import stdin',
        'from __future__ import (nested_scopes',
        'from __future__ import nested_scopes)',
        'from __future__ import nested_scopes,\ngenerators',
        'from sys import (stdin',
        'from sys import stdin)',
        'from sys import stdin, stdout,\nstderr',
        'from sys import stdin si',
        'from sys import stdin,'
        'from sys import (*)',
        'from sys import (stdin,, stdout, stderr)',
        'from sys import (stdin, stdout),',
        ]
    for stmt in succeed:
        compile(stmt, 'tmp', 'exec')
    for stmt in fail:
        raises(SyntaxError, compile, stmt, 'tmp', 'exec')

def test_future_error_offset():
    # points at the offending feature name, not the whole statement - see
    # test_future_import_errors_point_at_feature_name in apptest_exceptions.py
    with raises(SyntaxError) as excinfo:
        compile("from __future__ import bogus", "tmp", "exec")
    assert excinfo.value.offset == 24

def test_globals_warnings():
    import warnings
    for code in ('''
def wrong1():
    a = 1
    b = 2
    global a
    global b
''', '''
def wrong2():
    print x
    global x
''', '''
def wrong3():
    print x
    x = 2
    global x
'''):
        warnings.filterwarnings('error', module="<tmp>")
        try:
            raises(SyntaxError, compile, code, '<tmp>', 'exec')
        finally:
            warnings.resetwarnings()

def test_no_warning_run():
    import warnings
    for code in ['''
def testing():
    __class__ = 0
    def f():
        nonlocal __class__
        __class__ = 42
    f()
    return __class__
''', '''
class Y:
    class X:
        nonlocal __class__
        __class__ = 42
    assert locals()['__class__'] == 42
    # ^^^ but at the same place, reading '__class__' gives a NameError
    # in CPython 3.5.2.  Looks like a bug to me
def testing():
    return 42
''', '''
class Y:
    def f():
        __class__
    __class__ = 42
def testing():
    return Y.__dict__['__class__']
''', '''
class X:
    foobar = 42
    def f(self):
        return __class__.__dict__['foobar']
def testing():
    return X().f()
''',
        ]:
        warnings.filterwarnings('error', module="<tmp>")
        try:
            pycode = compile(code, '<tmp>', 'exec')
        finally:
            warnings.resetwarnings()
        d = {}
        exec(pycode, d, d)
        res = d['testing']()
        assert res == 42

def test_firstlineno():
    snippet = '''
def f(): "line 2"
if 3 and \\
   (4 and
      5):
    def g(): "line 6"
fline = f.__code__.co_firstlineno
gline = g.__code__.co_firstlineno
'''
    d = {}
    exec(snippet, d, d)
    assert d['fline'] == 2
    assert d['gline'] == 6

def test_firstlineno_decorators():
    snippet = '''
def foo(x): return x
@foo       # line 3
@foo       # line 4
def f():   # line 5
    pass   # line 6
fline = f.__code__.co_firstlineno
'''
    d = {}
    exec(snippet, d, d)
    assert d['fline'] == 3

def test_firstlineno_decorators_class():
    snippet = '''
def foo(x): return x
def f():
    @foo       # line 4
    @foo       # line 5
    class AWrong:
        pass   # line 7
Aline = f.__code__.co_consts[1].co_firstlineno
'''
    d = {}
    exec(snippet, d, d)
    assert d['Aline'] == 4

def test_mangling():
    snippet = '''
__g = "42"
class X(object):
    def __init__(self, u):
        self.__u = u
    def __f(__self, __n):
        global __g
        __NameError = NameError
        try:
            yield "found: " + __g
        except __NameError as __e:
            yield "not found: " + str(__e)
        del __NameError
        for __i in range(__self.__u * __n):
            yield locals()
result = X(2)
assert not hasattr(result, "__f")
result = list(result._X__f(3))
assert len(result) == 7
assert result[0].startswith("not found: ")
for d in result[1:]:
    for key, value in d.items():
        assert not key.startswith('__')
'''
    d = {}
    exec(snippet, d, d)

def test_ellipsis():
    snippet = '''
d = {}
d[...] = 12
assert next(iter(d)) is Ellipsis
'''
    d = {}
    exec(snippet, d, d)
    snip = "d[. . .]"
    raises(SyntaxError, compile, snip, '<test>', 'exec')

def test_chained_access_augassign():
    snippet = '''
class R(object):
   count = 0
c = 0
for i in [0,1,2]:
    c += 1
r = R()
for i in [0,1,2]:
    r.count += 1
c += r.count
l = [0]
for i in [0,1,2]:
    l[0] += 1
c += l[0]
l = [R()]
for i in [0]:
    l[0].count += 1
c += l[0].count
r.counters = [0]
for i in [0,1,2]:
    r.counters[0] += 1
c += r.counters[0]
r = R()
f = lambda : r
for i in [0,1,2]:
    f().count += 1
c += f().count
'''
    d = {}
    exec(snippet, d, d)
    assert d['c'] == 16

def test_augassign_with_tuple_subscript():
    snippet = '''
class D(object):
    def __getitem__(self, key):
        assert key == self.lastkey
        return self.lastvalue
    def __setitem__(self, key, value):
        self.lastkey = key
        self.lastvalue = value
def one(return_me=[1]):
    return return_me.pop()
d = D()
a = 15
d[1,2+a,3:7,...,1,] = 6
d[one(),17,slice(3,7),...,1] *= 7
result = d[1,17,3:7,Ellipsis,1]
'''
    d = {}
    exec(snippet, d, d)
    assert d['result'] == 42

def test_continue_in_finally():
    snippet = '''
def test():
    for abc in range(10):
        try: pass
        finally:
            continue       # 'continue' inside 'finally'

test()
'''
    exec(snippet, {})

def test_continue_in_nested_finally():
    snippet = '''
def test():
    for abc in range(10):
        try: pass
        finally:
            try:
                continue       # 'continue' inside 'finally'
            except:
                pass
test()
'''
    exec(snippet, {})

def test_really_nested_stuff():
    snippet = '''
def f(self):
    def get_nested_class():
        self
        class Test(object):
            def _STOP_HERE_(self):
                return _STOP_HERE_(self)
    get_nested_class()
f(42)
'''
    exec(snippet, {})
    # assert did not crash

def test_free_vars_across_class():
    snippet = '''
def f(x):
    class Test(object):
        def meth(self):
            return x + 1
    return Test()
res = f(42).meth()
'''
    d = {}
    exec(snippet, d, d)
    assert d['res'] == 43

def test_pick_global_names():
    snippet = '''
def f(x):
    def g():
        global x
        def h():
            return x
        return h()
    return g()
x = "global value"
res = f("local value")
'''
    d = {}
    exec(snippet, d, d)
    assert d['res'] == "global value"

def test_method_and_var():
    snippet = '''
def f():
    method_and_var = "var"
    class Test(object):
        def method_and_var(self):
            return "method"
        def test(self):
            return method_and_var
    return Test().test()
res = f()
'''
    d = {}
    exec(snippet, d, d)
    assert d['res'] == "var"

def test_yield_from():
    snippet = '''
def f():
    def generator2():
        yield 8
    def generator():
        yield from generator2()
    return next(generator())
res = f()
'''
    d = {}
    exec(snippet, d, d)
    assert d['res'] == 8

def test_dont_inherit_flag():
    # this test checks that compile() don't inherit the __future__ flags
    # of the hosting code.
    ns = {}
    exec('''
from __future__ import barry_as_FLUFL
# not a syntax error inside the exec!
exec(compile('x = 1 != 2', '?', 'exec', 0, 1))
''', ns)
    assert ns['x']

def test_dont_inherit_across_import(tmpdir):
    import os
    tmpdir = str(tmpdir)
    with open(os.path.join(tmpdir, 'test_dont_inherit_across_import.py'), 'w') as f:
        f.write('x = 1 != 2\n')
    copy = sys.path[:]
    sys.path.insert(0, tmpdir)
    ns = {}
    try:
        exec('''
from __future__ import barry_as_FLUFL
from test_dont_inherit_across_import import x
''', ns)
    finally:
        sys.path[:] = copy
    assert ns['x']

def test_filename_in_syntaxerror():
    with raises(SyntaxError) as excinfo:
        compile("""if 1:
        'unmatched_quote
        """, 'hello_world', 'exec')
    assert 'hello_world' in str(excinfo.value)

def test_del_None():
    snippet = '''if 1:
    try:
        del None
    except NameError:
        pass
'''
    raises(SyntaxError, compile, snippet, '<tmp>', 'exec')

def test_from_future_import():
    source = """from __future__ import with_statement
with somtehing as stuff:
    pass
        """
    code = compile(source, '<filename>', 'exec')
    assert code.co_filename == '<filename>'

    code = compile(source, '<filename2>', 'exec')
    assert code.co_filename == '<filename2>'

def test_assign_to_yield():
    code = 'def f(): (yield bar) += y'
    raises(SyntaxError, compile, code, '', 'single')

def test_invalid_genexp():
    code = 'dict(a = i for i in xrange(10))'
    raises(SyntaxError, compile, code, '', 'single')
