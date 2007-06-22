import autopath
from pypy.rlib.parsing.pypackrat import PackratParser
from pypy.lang.scheme.object import W_Pair, W_Fixnum, W_String, W_Symbol
from pypy.lang.scheme.object import W_Nil

DEBUG = False

class SchemeParser(PackratParser):
    r'''
    STRING:
        c = `\"([^\\\"]|\\\"|\\\\)*\"`
        IGNORE*
        return {W_String(c)};

    IDENTIFIER:
        c = `[\+\-\*\^\?a-zA-Z!<=>_~/$%&:][\+\-\*\^\?a-zA-Z0-9!<=>_~/$%&:]*`
        IGNORE*
        return {W_Symbol(c)};

    FIXNUM:
        c = `0|([1-9][0-9]*)`
        IGNORE*
        return {W_Fixnum(int(c))};

    IGNORE:
        ` |\n|\t|;[^\n]*`;
    
    EOF:
        !__any__;
    
    file:
        IGNORE*
        s = sexpr
        EOF
        return {s};
    
    sexpr:
        list
      | FIXNUM
      | IDENTIFIER
      | STRING;

    list:
        '('
        IGNORE*
        p = pair
        ')'
        IGNORE*
        return {p};

    pair:
        car = sexpr
        cdr = pair
        return {W_Pair(car, cdr)}
      | return {W_Nil()};
    '''

def parse(code):
    p = SchemeParser(code)
    return p.file()
