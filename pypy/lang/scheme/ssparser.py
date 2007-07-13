import autopath
from pypy.rlib.parsing.pypackrat import PackratParser
from pypy.rlib.parsing.makepackrat import BacktrackException, Status
from pypy.lang.scheme.object import W_Pair, W_Integer, W_String, W_Identifier, \
        W_Nil, W_Boolean, W_Real, Literal

def unquote(s):
    str_lst = []
    last_ch = ''
    for c in s[1:]:
        if last_ch == '\\' and c == '"':
            pass
        else:
            str_lst.append(last_ch)

        last_ch = c

    return ''.join(str_lst)

class SchemeParser(PackratParser):
    r"""
    STRING:
        c = `\"([^\\\"]|\\\"|\\\\)*\"`
        IGNORE*
        return {W_String(unquote(c))};

    IDENTIFIER:
        c = `[\+\-\*\^\?a-zA-Z!<=>_~/$%&:][\+\-\*\^\?a-zA-Z0-9!<=>_~/$%&:]*`
        IGNORE*
        return {W_Identifier(c)};

    FIXNUM:
        c = `\-?(0|([1-9][0-9]*))`
        IGNORE*
        return {W_Integer(int(c))};

    FLOAT:
        c = `\-?[0-9]*\.[0-9]*`
        IGNORE*
        return {W_Real(float(c))};

    BOOLEAN:
        c = `#(t|f)`
        IGNORE*
        return {W_Boolean(c[1] == 't')};

    IGNORE:
        ` |\n|\t|;[^\n]*`;
    
    EOF:
        !__any__;
    
    file:
        IGNORE*
        s = sexpr*
        EOF
        return {s};
    
    literal:
       `'`
       s = sexpr
       return {Literal(s)};
    
    sexpr:
        list
      | literal
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
        '.'
        IGNORE*
        cdr = sexpr
        return {W_Pair(car, cdr)}
      | car = sexpr
        cdr = pair
        return {W_Pair(car, cdr)}
      | return {W_Nil()};
    """

def parse(code):
    p = SchemeParser(code)
    return p.file()

