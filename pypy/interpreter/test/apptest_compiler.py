from pytest import raises, skip


def test_bom_with_future():
    s = '\xef\xbb\xbffrom __future__ import division\nx = 1/2'
    ns = {}
    exec s in ns
    assert ns["x"] == .5

def test_values_of_different_types():
    exec "a = 0; b = 0L; c = 0.0; d = 0j"
    assert type(a) is int
    assert type(b) is long
    assert type(c) is float
    assert type(d) is complex

def test_values_of_different_types_in_tuples():
    exec "a = ((0,),); b = ((0L,),); c = ((0.0,),); d = ((0j,),)"
    assert type(a[0][0]) is int
    assert type(b[0][0]) is long
    assert type(c[0][0]) is float
    assert type(d[0][0]) is complex

def test_zeros_not_mixed():
    import math
    code = compile("x = -0.0; y = 0.0", "<test>", "exec")
    consts = code.co_consts
    x, y, z = consts
    assert isinstance(x, float) and isinstance(y, float)
    assert math.copysign(1, x) != math.copysign(1, y)
    ns = {}
    exec "z1, z2 = 0j, -0j" in ns
    assert math.atan2(ns["z1"].imag, -1.) == math.atan2(0., -1.)
    assert math.atan2(ns["z2"].imag, -1.) == math.atan2(-0., -1.)

def test_zeros_not_mixed_in_tuples():
    import math
    exec "a = (0.0, 0.0); b = (-0.0, 0.0); c = (-0.0, -0.0)"
    assert math.copysign(1., a[0]) == 1.0
    assert math.copysign(1., a[1]) == 1.0
    assert math.copysign(1., b[0]) == -1.0
    assert math.copysign(1., b[1]) == 1.0
    assert math.copysign(1., c[0]) == -1.0
    assert math.copysign(1., c[1]) == -1.0

def test_zeros_not_mixed_in_lambdas():
    import math
    code = compile("x = lambda: -0.0; y = lambda: 0.0", "<test>", "exec")
    consts = code.co_consts
    x, y, z = consts
    assert isinstance(x, type(code)) and isinstance(y, type(code))
    assert x is not y
    assert x != y

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

def test_remove_ending():
    source = """def f():
            return 3
"""
    exec source
    code = f.func_code
    import dis, sys, StringIO
    s = StringIO.StringIO()
    so = sys.stdout
    sys.stdout = s
    try:
        dis.dis(code)
    finally:
        sys.stdout = so
    output = s.getvalue()
    assert output.count('LOAD_CONST') == 1

def test_tuple_constants():
    ns = {}
    exec "x = (1, 0); y = (1L, 0L)" in ns
    assert isinstance(ns["x"][0], int)
    assert isinstance(ns["y"][0], long)

def test_folding_of_binops_on_constants():
    def disassemble(func):
        from StringIO import StringIO
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
        print asm
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
                print a
                return 1
            """

    exec source
    code = _f.func_code

    import StringIO, sys, dis
    s = StringIO.StringIO()
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
    exec source
    code = _f.func_code

    import StringIO, sys, dis
    s = StringIO.StringIO()
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
    source = """def _f(a):
            return a.f(a=a)
        """
    exec source
    code = _f.func_code

    import StringIO, sys, dis
    s = StringIO.StringIO()
    out = sys.stdout
    sys.stdout = s
    try:
        dis.dis(code)
    finally:
        sys.stdout = out
    output = s.getvalue()
    assert "CALL_METHOD" in output

def test_interned_strings():
    source = """x = ('foo_bar42', 5); y = 'foo_bar42'; z = x[0]"""
    exec source
    assert y is z

def test_indentation_error():
    source = """if 1:
        x
         y
        """
    try:
        exec source
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
        exec source
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

def test_repr_vs_str():
    source1 = "x = (\n"
    source2 = "x = (\n\n"
    try:
        exec source1
    except SyntaxError as err1:
        pass
    else:
        raise Exception("DID NOT RAISE")
    try:
        exec source2
    except SyntaxError as err2:
        pass
    else:
        raise Exception("DID NOT RAISE")
    assert str(err1) != str(err2)
    assert repr(err1) != repr(err2)
    err3 = eval(repr(err1))
    assert str(err3) == str(err1)
    assert repr(err3) == repr(err1)

def test_encoding():
    code = b'# -*- coding: badencoding -*-\npass\n'
    raises(SyntaxError, compile, code, 'tmp', 'exec')
    code = u"# -*- coding: utf-8 -*-\npass\n"
    raises(SyntaxError, compile, code, 'tmp', 'exec')
    code = 'u"\xc2\xa4"\n'
    assert eval(code) == u'\xc2\xa4'
    code = u'u"\xc2\xa4"\n'
    assert eval(code) == u'\xc2\xa4'
    code = '# -*- coding: latin1 -*-\nu"\xc2\xa4"\n'
    assert eval(code) == u'\xc2\xa4'
    code = '# -*- coding: utf-8 -*-\nu"\xc2\xa4"\n'
    assert eval(code) == u'\xa4'
    code = '# -*- coding: iso8859-15 -*-\nu"\xc2\xa4"\n'
    assert eval(code) == u'\xc2\u20ac'
    import sys
    if sys.version_info < (2, 7, 9):
        skip()
    code = 'u"""\\\n# -*- coding: utf-8 -*-\n\xc2\xa4"""\n'
    assert eval(code) == u'# -*- coding: utf-8 -*-\n\xc2\xa4'

def test_asterror_has_line_without_file():
    code = u"print(1)\na/2 = 5\n"
    with raises(SyntaxError) as excinfo:
        compile(code, 'not a file!', 'exec')
    assert excinfo.value.text == "a/2 = 5\n"
