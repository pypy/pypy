from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.object import W_Pair, W_Fixnum, W_String, W_Symbol
from pypy.lang.scheme.object import W_Nil

def unwrap(w_obj):
    """for testing purposes: unwrap a scheme object into a python object"""
    if isinstance(w_obj, W_Fixnum):
        return w_obj.to_number()
    elif isinstance(w_obj, W_String):
        return w_obj.strval
    elif isinstance(w_obj, W_Symbol):
        return w_obj.name
    elif isinstance(w_obj, W_Pair):
        result = []
        while not isinstance(w_obj, W_Nil):
            result.append(unwrap(w_obj.car))
            w_obj = w_obj.cdr
        return result
    raise NotImplementedError("don't know what to do with: %s" % (w_obj, ))
    
def test_simple():
    w_fixnum = parse(r'''1''')
    assert isinstance(w_fixnum, W_Fixnum)
    w_fixnum = parse(r'''0''')
    assert isinstance(w_fixnum, W_Fixnum)
    w_fixnum = parse(r'''1123''')
    assert isinstance(w_fixnum, W_Fixnum)
    w_fixnum = parse(r'''abfa__''')
    assert isinstance(w_fixnum, W_Symbol)
    w_fixnum = parse(r'''+''')
    assert isinstance(w_fixnum, W_Symbol)
    t = parse(r'''"don't beleive \"them\""''')
    assert isinstance(t, W_String)
    w_list = parse(r'''(+ 1 2)''')
    assert isinstance(w_list, W_Pair)
    assert isinstance(w_list.car, W_Symbol)
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
    assert isinstance(t.car, W_Symbol)
    assert isinstance(t.cdr, W_Nil)


