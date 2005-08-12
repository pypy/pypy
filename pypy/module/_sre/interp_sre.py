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
    return code < 128 and ascii_char_info[code] & 1

def is_uni_digit(space, w_char):
    return space.is_true(space.call_method(w_char, "isdigit"))

def is_space(space, w_char):
    code = space.int_w(space.ord(w_char))
    return code < 128 and ascii_char_info[code] & 2

def is_uni_space(space, w_char):
    return space.is_true(space.call_method(w_char, "isspace"))

def is_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    return code < 128 and ascii_char_info[code] & 16

def is_uni_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    w_unichar = space.newunicode([code])
    isalnum = space.is_true(space.call_method(w_unichar, "isalnum"))
    return isalnum or code == underline

def is_loc_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    if code > 255:
        return False
    # Need to use this new w_char_not_uni from here on, because this one is
    # guaranteed to be not unicode.
    w_char_not_uni = space.wrap(chr(code))
    isalnum = space.is_true(space.call_method(w_char_not_uni, "isalnum"))
    return isalnum or code == underline

def is_linebreak(space, w_char):
    return space.int_w(space.ord(w_char)) == linebreak

def is_uni_linebreak(space, w_char):
    code = space.int_w(space.ord(w_char))
    return uni_linebreaks.has_key(code)


#### Category dispatch

def category_dispatch(space, w_chcode, w_char):
    chcode = space.int_w(w_chcode)
    if chcode >= len(category_dispatch_table):
        return space.newbool(False)
    function, negate = category_dispatch_table[chcode]
    result = function(space, w_char)
    if negate:
        return space.newbool(not result)
    else:
        return space.newbool(result)

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

##### At dispatch

class MatchContext:
    # XXX This is not complete. It's tailored to at dispatch currently.
    
    def __init__(self, space, w_string, string_position, end):
        self.space = space
        self.w_string = w_string
        self.string_position = string_position
        self.end = end

    def peek_char(self, peek=0):
        return self.space.getitem(self.w_string,
                                   self.space.wrap(self.string_position + peek))

    def remaining_chars(self):
        return self.end - self.string_position

    def at_beginning(self):
        return self.string_position == 0

    def at_end(self):
        return self.string_position == self.end

    def at_linebreak(self):
        return not self.at_end() and is_linebreak(self.space, self.peek_char())

    def at_boundary(self, word_checker):
        if self.at_beginning() and self.at_end():
            return False
        that = not self.at_beginning() \
                            and word_checker(self.space, self.peek_char(-1))
        this = not self.at_end() \
                            and word_checker(self.space, self.peek_char())
        return this != that

def at_dispatch(space, w_atcode, w_string, w_string_position, w_end):
    # XXX temporary ugly method signature until we can call this from
    # interp-level only
    atcode = space.int_w(w_atcode)
    if atcode >= len(at_dispatch_table):
        return space.newbool(False)
    context = MatchContext(space, w_string, space.int_w(w_string_position),
                                                            space.int_w(w_end))
    function, negate = at_dispatch_table[atcode]
    result = function(space, context)
    if negate:
        return space.newbool(not result)
    else:
        return space.newbool(result)

def at_beginning(space, ctx):
    return ctx.at_beginning()

def at_beginning_line(space, ctx):
    return ctx.at_beginning() or is_linebreak(space, ctx.peek_char(-1))
    
def at_end(space, ctx):
    return ctx.at_end() or (ctx.remaining_chars() == 1 and ctx.at_linebreak())

def at_end_line(self, ctx):
    return ctx.at_linebreak() or ctx.at_end()

def at_end_string(self, ctx):
    return ctx.at_end()

def at_boundary(self, ctx):
    return ctx.at_boundary(is_word)

def at_loc_boundary(self, ctx):
    return ctx.at_boundary(is_loc_word)

def at_uni_boundary(self, ctx):
    return ctx.at_boundary(is_uni_word)

# Maps opcodes by indices to (function, negate) tuples.
at_dispatch_table = [
    (at_beginning, False), (at_beginning_line, False), (at_beginning, False),
    (at_boundary, False), (at_boundary, True),
    (at_end, False), (at_end_line, False), (at_end_string, False),
    (at_loc_boundary, False), (at_loc_boundary, True), (at_uni_boundary, False),
    (at_uni_boundary, True)
]
