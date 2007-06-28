import autopath
from pypy.rlib.parsing.pypackrat import PackratParser
from pypy.rlib.parsing.makepackrat import BacktrackException, Status
from pypy.lang.scheme.object import W_Pair, W_Fixnum, W_String, W_Identifier
from pypy.lang.scheme.object import W_Nil, W_Boolean, W_Float

def unquote(s):
    return s.replace('\\"', '"')

class SchemeParser(PackratParser):
    r'''
    STRING:
        c = `\"([^\\\"]|\\\"|\\\\)*\"`
        IGNORE*
        return {W_String(unquote(c[1:-1]))};

    IDENTIFIER:
        c = `[\+\-\*\^\?a-zA-Z!<=>_~/$%&:][\+\-\*\^\?a-zA-Z0-9!<=>_~/$%&:]*`
        IGNORE*
        return {W_Identifier(c)};

    FIXNUM:
        c = `\-?(0|([1-9][0-9]*))`
        IGNORE*
        return {W_Fixnum(c)};

    FLOAT:
        c = `\-?[0-9]*\.[0-9]*`
        IGNORE*
        return {W_Float(c)};

    BOOLEAN:
        c = `#(t|f)`
        IGNORE*
        return {W_Boolean(c[-1] == 't')};

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
      | FLOAT
      | FIXNUM
      | BOOLEAN
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
