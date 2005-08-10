from pypy.interpreter.baseobjspace import ObjSpace

#### Category helpers

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

def is_digit(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(code < 128 and ascii_char_info[code] & 1)

def is_uni_digit(space, w_char):
    return space.newbool(space.is_true(space.call_method(w_char, "isdigit")))

def is_space(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(code < 128 and ascii_char_info[code] & 2)

def is_uni_space(space, w_char):
    return space.newbool(space.is_true(space.call_method(w_char, "isspace")))

def is_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(code < 128 and ascii_char_info[code] & 16)

def is_uni_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    w_unichar = space.newunicode([code])
    isalnum = space.is_true(space.call_method(w_unichar, "isalnum"))
    return space.newbool(isalnum or code == underline)

def is_loc_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    if code > 255:
        return space.newbool(False)
    # Need to use this new w_char_not_uni from here on, because this one is
    # guaranteed to be not unicode.
    w_char_not_uni = space.wrap(chr(code))
    isalnum = space.is_true(space.call_method(w_char_not_uni, "isalnum"))
    return space.newbool(isalnum or code == underline)

def is_linebreak(space, w_char):
    return space.newbool(space.int_w(space.ord(w_char)) == linebreak)

def is_uni_linebreak(space, w_char):
    code = space.int_w(space.ord(w_char))
    return space.newbool(uni_linebreaks.has_key(code))


#### Category dispatch

def category_dispatch(space, w_chcode, w_char):
    chcode = space.int_w(w_chcode)
    if chcode >= len(category_dispatch_table):
        return space.newbool(False)
    w_function, negate = category_dispatch_table[chcode]
    w_result = w_function(space, w_char)
    if negate:
        return space.newbool(not space.is_true(w_result))
    else:
        return w_result

# Maps opcodes by indices to (function, negate) tuples.
category_dispatch_table = [
    (is_digit, False), (is_digit, True), (is_space, False),
    (is_space, True), (is_word, False), (is_word, True),
    (is_linebreak, False), (is_linebreak, True), (is_loc_word, False),
    (is_loc_word, True), (is_uni_digit, False), (is_uni_digit, True),
    (is_uni_space, False), (is_uni_space, True), (is_uni_word, False),
    (is_uni_word, True), (is_uni_linebreak, False),
    (is_uni_linebreak, True)
]
