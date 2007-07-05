import py
from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.object import W_Boolean, W_Float, W_Fixnum, W_String
from pypy.lang.scheme.object import W_Pair, W_Nil, W_Symbol, W_Identifier

def unwrap(w_obj):
    """for testing purposes: unwrap a scheme object into a python object"""
    if isinstance(w_obj, W_Float):
        return w_obj.to_number()
    elif isinstance(w_obj, W_Fixnum):
        return w_obj.to_number()
    elif isinstance(w_obj, W_String):
        return w_obj.strval
    elif isinstance(w_obj, W_Identifier):
        return w_obj.name
    elif isinstance(w_obj, W_Symbol):
        return w_obj.name
    elif isinstance(w_obj, W_Boolean):
        return w_obj.boolval
    elif isinstance(w_obj, W_Pair):
        result = []
        while not isinstance(w_obj, W_Nil):
            result.append(unwrap(w_obj.car))
            w_obj = w_obj.cdr
        return result
    raise NotImplementedError("don't know what to do with: %s" % (w_obj, ))

def test_simple():
    w_fixnum = parse('1')
    assert isinstance(w_fixnum, W_Fixnum)
    assert unwrap(w_fixnum) == 1
    w_fixnum = parse('0')
    assert unwrap(w_fixnum) == 0
    assert isinstance(w_fixnum, W_Fixnum)
    w_fixnum = parse('1123')
    assert unwrap(w_fixnum) == 1123
    assert isinstance(w_fixnum, W_Fixnum)
    w_fixnum = parse('abfa__')
    assert isinstance(w_fixnum, W_Identifier)
    t = parse(r'''"don't believe \"them\""''')
    assert isinstance(t, W_String)
    assert unwrap(t) == 'don\'t believe "them"'

def test_objects():
    w_fixnum = parse('-12345')
    assert isinstance(w_fixnum, W_Fixnum)
    assert unwrap(w_fixnum) == -12345

    w_float = parse('123456.1234')
    assert isinstance(w_float, W_Float)
    assert unwrap(w_float) == 123456.1234
    w_float = parse('-123456.1234')
    assert isinstance(w_float, W_Float)
    assert unwrap(w_float) == -123456.1234

def test_sexpr():
    w_list = parse('( 1 )')
    assert isinstance(w_list, W_Pair)
    assert isinstance(w_list.car, W_Fixnum)
    assert isinstance(w_list.cdr, W_Nil)

    #w_list = parse('()')
    #assert isinstance(w_list, W_Nil)

    w_list = parse('(+ 1 2)')
    assert isinstance(w_list, W_Pair)
    assert isinstance(w_list.car, W_Identifier)
    assert isinstance(w_list.cdr, W_Pair)
    assert isinstance(w_list.cdr.car, W_Fixnum)
    assert isinstance(w_list.cdr.cdr.car, W_Fixnum)
    assert isinstance(w_list.cdr.cdr.cdr, W_Nil)

def test_complex_sexpr():
    #parse more complex sexpr
    t = parse(r'''
        (define (fac n) ; comment
            (if (< n 2) n
                (* (fac (- n 1)) n)))
        ''')
    assert isinstance(t, W_Pair)
    assert unwrap(t) == ['define', ['fac', 'n'],
                            ['if', ['<', 'n', 2], 'n',
                                   ['*', ['fac', ['-', 'n', 1]], 'n']]]

def test_ident_gen():
    ch_list = "+-*/azAZ<=>-_~!$%&:?^"
    for char in ch_list:
        yield check_ident_ch, char

def check_ident_ch(char):
    t = parse("(" + char + ")")
    assert isinstance(t, W_Pair)
    assert isinstance(t.car, W_Identifier)
    assert unwrap(t.car) == char
    assert isinstance(t.cdr, W_Nil)

def test_truth_values():
    t = parse("#f")
    assert unwrap(t) == False
    t = parse("#t")
    assert unwrap(t) == True

def test_list_dotted():
    t = parse("(1 . 2)")
    assert isinstance(t, W_Pair)
    assert unwrap(t.car) == 1
    assert unwrap(t.cdr) == 2

    t = parse("(1 . (2 . 3))")
    assert unwrap(t.car) == 1
    assert unwrap(t.cdr.car) == 2
    assert unwrap(t.cdr.cdr) == 3

    t = parse("(1 . (2 . (3 . ())))")
    assert unwrap(t) == [1, 2, 3]

def test_list_mixed():
    t = parse("(1 2 . 3)")
    assert unwrap(t.car) == 1
    assert unwrap(t.cdr.car) == 2
    assert unwrap(t.cdr.cdr) == 3

    t = parse("(1 2 . (3 4))")
    assert unwrap(t) == [1, 2, 3, 4]

