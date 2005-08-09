from pypy.interpreter.baseobjspace import ObjSpace

_ascii_char_info = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 6, 2,
2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25, 25, 25, 25, 25, 25, 25, 25,
25, 25, 0, 0, 0, 0, 0, 0, 0, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24,
24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 0, 0,
0, 0, 16, 0, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24,
24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 0, 0, 0, 0, 0 ]

_linebreak = ord("\n")

def _is_digit(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(code < 128 and _ascii_char_info[code] & 1)

def _is_space(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(code < 128 and _ascii_char_info[code] & 2)

def _is_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(code < 128 and _ascii_char_info[code] & 16)

def _is_linebreak(space, w_char):
    return space.newbool(space.int_w(space.ord(w_char)) == _linebreak)
