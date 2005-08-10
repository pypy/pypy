from pypy.interpreter.baseobjspace import ObjSpace

ascii_char_info = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 6, 2,
2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25, 25, 25, 25, 25, 25, 25, 25,
25, 25, 0, 0, 0, 0, 0, 0, 0, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24,
24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 0, 0,
0, 0, 16, 0, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24,
24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 0, 0, 0, 0, 0 ]

linebreak = ord("\n")
underline = ord("_")

# Static list of all unicode codepoints reported by Py_UNICODE_ISLINEBREAK.
# Using a dict as a poor man's set.
uni_linebreaks = {10: True, 13: True, 28: True, 29: True, 30: True, 133: True,
                  8232: True, 8233: True}

def _is_digit(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(code < 128 and ascii_char_info[code] & 1)

def _is_space(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(code < 128 and ascii_char_info[code] & 2)

def _is_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(code < 128 and ascii_char_info[code] & 16)

def _is_uni_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    w_unichar = space.newunicode([code])
    isalnum = space.is_true(space.call_method(w_unichar, "isalnum"))
    return space.newbool(isalnum or code == underline)

def _is_loc_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    if code > 255:
        return space.newbool(False)
    # Need to use this new w_char_not_uni from here on, because this one is
    # guaranteed to be not unicode.
    w_char_not_uni = space.wrap(chr(code))
    isalnum = space.is_true(space.call_method(w_char_not_uni, "isalnum"))
    return space.newbool(isalnum or code == underline)

def _is_linebreak(space, w_char):
    return space.newbool(space.int_w(space.ord(w_char)) == linebreak)

def _is_uni_linebreak(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(uni_linebreaks.has_key(code))
