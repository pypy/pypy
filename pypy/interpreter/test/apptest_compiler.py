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
