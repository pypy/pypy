# coding=utf-8

import py
from prolog.interpreter.continuation import Engine
from prolog.interpreter.parsing import get_engine
from prolog.interpreter.stream import PrologInputStream , PrologOutputStream
from prolog.interpreter.test.tool import create_file, delete_file, \
prolog_raises, assert_true, assert_false, file_content
from prolog.interpreter import term
from prolog.interpreter.heap import Heap
from prolog.builtin.streams import impl_current_input, impl_current_output
from prolog.builtin.streams import _strip

def test_current_stream_after_startup():
    e = get_engine("")
    assert isinstance(e.streamwrapper.current_instream, PrologInputStream)
    assert isinstance(e.streamwrapper.current_outstream, PrologOutputStream)
    assert e.streamwrapper.current_instream.fd() == 0
    assert e.streamwrapper.current_outstream.fd() == 1

def test_open():
    src = "__src__"
    create_file(src, "")
    try:
        e = Engine()
        assert_true("open('%s', read, S)." % src, e)
        assert len(e.streamwrapper.streams) == 3

        prolog_raises("existence_error(X, Y)", "open('does_not_exist', read, S)")
        prolog_raises("type_error(X, Y)", "open('%s', read, a)" % src)
        assert_true("open('%s', write, S)." % src)
        assert_true("open('%s', append, S)." % src)
        prolog_raises("domain_error(X, Y)", "open('%s', asdsadsad, X)")
    finally:
        delete_file(src)

def test_unify_default_alias():
    src = "__src__"
    create_file(src, "")
    try:
        e = Engine()
        assert_true("open('%s', read, S)." % src, e)
        assert len(e.streamwrapper.aliases) == 3
        for key in e.streamwrapper.aliases.keys():
            if not key.endswith("_0") and not key.endswith("_1"):
                alias = key
        assert_true("S = '%s'." % alias, e)
    finally:
        delete_file(src)

def test_unify_explicit_alias():
    src = "__src__"
    create_file(src, "")
    try:
        assert_true("open('%s', read, S, [alias(s)]), S = s." % src)
    finally:
        delete_file(src)

def test_open_alias_option():
    src = "__src__"
    create_file(src, "abc")
    try:
        assert_true("""
        open('%s', read, S, [alias(input)]),
        get_char(input, X), X = a,
        close(input).
        """ % src)
    finally:
        delete_file(src)

    create_file(src, "")
    e = Engine()
    try:
        assert_true("open('%s', read, S, [alias(blub)])." % src, e)
        assert len(e.streamwrapper.aliases) == 3
        assert_true("close(blub).", e)
        assert len(e.streamwrapper.aliases) == 2
    finally:
        delete_file(src)

def test_close():
    src = "__src__"
    create_file(src, "")

    try:
        e = get_engine("""
        :- open('%s', read, S), close(S).
        """ % src)
        assert len(e.streamwrapper.streams) == 2
        assert 0 in e.streamwrapper.streams
        assert 1 in e.streamwrapper.streams
        prolog_raises("instantiation_error", "close(X)")
        prolog_raises("domain_error(stream, Y)", "close(a)")
    finally:
        delete_file(src)

def test_get_char():
    src = "__src__"
    create_file(src, "aü½")
    try:
        assert_true("""
        open('%s', read, S),
        get_char(S, C), C = 'a',
        get_char(S, D), D = 'ü', 
        get_char(S, E), E = '½', 
        close(S).
        """ % src)
        assert_false("""
        open('%s', read, S), 
        get_char(S, some_atom).
        """ % src)
    finally:
        delete_file(src)

def test_get_char_at_eof():
    src = "__empty__"
    create_file(src, "")
    try:
        assert_true("""
        open('%s', read, S),
        get_char(S, C), C = end_of_file,
        close(S).
        """ % src)
    finally:
        delete_file(src)

def test_get_byte():
    src = "__src__"
    create_file(src, "\xa4\x17\xcf")
    try:
        assert_true("""
        open('%s', read, S),
        get_byte(S, B), B = 164,
        get_byte(S, C), C = 23,
        get_byte(S, D), D = 207,
        get_byte(S, E), E = -1,
        close(S).
        """ % src)
    finally:
        delete_file(src)

def test_get_code():
    src = "__src__"
    create_file(src, "a1¼")
    try:
        assert_true("""
        open('%s', read, S),
        get_code(S, B), B = 97,
        get_code(S, C), C = 49,
        get_code(S, D), D = 194,
        get_code(S, E), E = 188,
        get_code(S, F), F = -1,
        close(S).
        """ % src)
    finally:
        delete_file(src)

def test_at_end_of_stream_1():
    src = "__src__"
    create_file(src, "abc")
    try:
        assert_true("""
        open('%s', read, S),
        get_byte(S, B1),
        get_byte(S, B2),
        get_byte(S, B3),
        at_end_of_stream(S),
        close(S).
        """ % src)
        assert_false("""
        open('%s', read, S),
        get_byte(S, B1),
        get_byte(S, B2),
        at_end_of_stream(S).
        """ % src)
    finally:
        delete_file(src)

def XXX_test_at_end_of_stream_or():
    src = "__src__"
    create_file(src, "a")
    try:
        assert_false("""
        open('%s', read, S),
        (at_end_of_stream(S); at_end_of_stream(S)).
        """ % src)
    finally:
        delete_file(src)

def test_at_end_of_stream_empty():
    src = "__src__"
    create_file(src, "")
    try:
        assert_true("""
        open('%s', read, S),
        at_end_of_stream(S),
        close(S).
        """ % src)
    finally:
        delete_file(src)

def test_peek_char():
    src = "__src__"
    empty = "__empty__"
    create_file(src, "aü¼")
    create_file(empty, "")
    try:
        assert_true("""
        open('%s', read, S),
        peek_char(S, C), C = 'a',
        peek_char(S, D), D = 'a',
        get_char(S, _),
        peek_char(S, E), E = 'ü',
        peek_char(S, F), F = 'ü',
        get_char(S, _),
        peek_char(S, G), G = '¼',
        get_char(S, _),
        peek_char(S, Z), Z = end_of_file,
        close(S).
        """ % src)

        assert_true("""
        open('%s', read, S),
        peek_char(S, end_of_file),
        close(S).
        """ % empty)
    finally:
        delete_file(src)
        delete_file(empty)

def test_peek_byte():
    src = "__src__"
    empty = "__empty__"
    create_file(src, "\x94\xef")
    create_file(empty, "")
    try:
        assert_true("""
        open('%s', read, S),
        peek_byte(S, C), C = 148,
        peek_byte(S, D), D = 148,
        get_byte(S, _),
        peek_byte(S, E), E = 239,
        peek_byte(S, F), F = 239,
        get_byte(S, _),
        peek_byte(S, Z), Z = -1,
        close(S).
        """ % src)

        assert_true("""
        open('%s', read, S),
        peek_byte(S, -1),
        close(S).
        """ % empty)
    finally:
        delete_file(src)
        delete_file(empty)

def test_peek_code():
    src = "__src__"
    empty = "__empty__"
    create_file(src, "¼")
    create_file(empty, "")
    try:
        assert_true("""
        open('%s', read, S),
        peek_code(S, C), C = 194,
        peek_code(S, D), D = 194,
        get_code(S, _),
        peek_code(S, E), E = 188,
        get_code(S, _),
        peek_code(S, F), F = -1,
        close(S).
        """ % src)

        assert_true("""
        open('%s', read, S),
        peek_code(S, -1),
        close(S).
        """ % empty)
    finally:
        delete_file(src)
        delete_file(empty)

def test_put_char():
    src = "__src__"
    target = "__target__"
    content = "aö½"
    create_file(src, content)
    create_file(target, "")
    try:
        assert_true("""
        open('%s', read, R), open('%s', write, W),
        get_char(R, C1), put_char(W, C1),
        get_char(R, C2), put_char(W, C2),
        get_char(R, C3), put_char(W, C3),
        close(R), close(W).
        """ % (src, target))
        assert content == file_content(src)
    finally:
        delete_file(src)
        delete_file(target)

def test_put_char_type_error():
    src = "__src__"
    create_file(src, "") 
    try:
        prolog_raises("type_error(X, Y)", """
        open('%s', write, S),
        put_char(S, aa)
        """ % src)
    finally:
        delete_file(src)

def test_put_byte():
    target = "__target__"
    create_file(target, "")
    try:
        assert_true("""
        open('%s', write, S),
        put_byte(S, 97),
        put_byte(S, 194),
        put_byte(S, 165),
        close(S).
        """ % target)
        assert file_content(target) == "a¥"
    finally:
        delete_file(target)

def test_put_byte_below_zero():
    target = "__xxx__"
    create_file(target, "")
    try:
        prolog_raises("type_error(byte, X)", """
        open('%s', write, S),
        put_byte(S, -1)
        """ % target)
    finally:
        delete_file(target)

def test_current_input():
    e = Engine()
    h = Heap()
    X = h.newvar()
    impl_current_input(e, h, X)
    assert X.dereference(h).name() == e.streamwrapper.current_instream.alias

def test_current_input_2():
    src = "__src__"
    create_file(src, "")
    try:
        assert_true("""
        open('%s', read, S),
        set_input(S),
        close(S).
        """ % src)
    finally:
        delete_file(src)
    
def test_current_output():
    e = Engine()
    h = Heap()
    X = h.newvar()
    impl_current_output(e, h, X)
    assert X.dereference(h).name() == e.streamwrapper.current_outstream.alias

def test_current_input_output_domain_error():
    prolog_raises("domain_error(stream, X)", "current_input(f(a))")
    prolog_raises("domain_error(stream, X)", "current_output(f(a))")

def test_permission_error():
    prolog_raises("permission_error(X, Y, Z)", """
    current_input(S),
    put_char(S, a)
    """)
    src = "__src__"
    create_file(src, "")
    try:
        prolog_raises("permission_error(X, Y, Z)", """
        open('%s', read, S),
        put_char(S, a)
        """ % src)
    finally:
        delete_file(src)

    prolog_raises("permission_error(X, Y, Z)", """
    current_output(S),
    get_char(S, a)
    """)

def test_set_input():
    src = "__src__"
    create_file(src, "")
    try:
        e = Engine()
        assert_true("""
        open('%s', read, S),
        set_input(S),
        current_input(S).
        """ % src, e)
        assert len(e.streamwrapper.streams) == 3
        for key in e.streamwrapper.streams.keys():
            if key not in [0, 1]:
                fd = key
                break
        assert e.streamwrapper.current_instream.fd() == fd
    finally:
        delete_file(src)

def test_close_current_input():
    src = "__src__"
    create_file(src, "")
    try:
        e = Engine()
        w = e.streamwrapper
        assert w.current_instream.alias == "$stream_0"
        assert_true("""
        open('%s', read, S),
        set_input(S),
        close(S).
        """ % src, e)
        assert w.current_instream.alias == "$stream_0"
    finally:
        delete_file(src)

def test_set_output():
    src = "__src__"
    create_file(src, "")
    try:
        e = Engine()
        assert_true("""
        open('%s', write, S),
        set_output(S),
        current_output(S).
        """ % src, e)
        assert len(e.streamwrapper.streams) == 3
        for key in e.streamwrapper.streams.keys():
            if key not in [0, 1]:
                fd = key
                break
        assert e.streamwrapper.current_outstream.fd() == fd
    finally:
        delete_file(src)

def test_close_current_output():
    src = "__src__"
    create_file(src, "")
    try:
        e = Engine()
        w = e.streamwrapper
        assert w.current_outstream.alias == "$stream_1"
        assert_true("""
        open('%s', write, S),
        set_output(S),
        close(S).
        """ % src, e)
        assert w.current_outstream.alias == "$stream_1"
    finally:
        delete_file(src)

def test_set_input_with_output_and_otherway_round():
    src = "__src__"
    create_file(src, "")
    try:
        prolog_raises("permission_error(X, Y, Z)", """
        open('%s', write, S),
        set_input(S)
        """ % src)
        
        prolog_raises("permission_error(X, Y, Z)", """
        open('%s', read, S),
        set_output(S)
        """ % src)
    finally:
        delete_file(src)

def test_seek():
    src = "__src__"
    create_file(src, "\xab\xcd\xef")
    try:
        assert_true("""
        open('%s', read, S),
        seek(S, 1, current, 1), peek_byte(S, 205),
        seek(S, -1, current, 0), peek_byte(S, 171),
        seek(S, -1, eof, 2), peek_byte(S, 239),
        seek(S, 0, eof, 3), peek_byte(S, -1),
        seek(S, 0, bof, 0), peek_byte(S, 171),
        seek(S, -3, eof, 0), peek_byte(S, 171),
        seek(S, 1000, bof, 1000), peek_byte(S, -1),
        close(S).
        """ % src)
    finally:
        delete_file(src)

def test_seek_domain_error():
    src = "__src__"
    create_file(src, "")
    try:
        prolog_raises("domain_error(seek_method, Y)", """
        open('%s', read, S),
        seek(S, 1, ajhdsasd, P)
        """ % src)

        prolog_raises("domain_error(position, X)", """
        open('%s', read, S),
        seek(S, -1, bof, A)
        """ % src)
    finally:
        delete_file(src)

def test_nl():
    src = "__src__"
    create_file(src, "")
    try:
        assert_true("""
        open('%s', write, S),
        nl(S),
        close(S).
        """ % src)
        assert "\n" == file_content(src)
    finally:
        delete_file(src)

def test_write():
    src = "__src__"
    term = "f(a, b, g(e))"
    create_file(src, "")
    try:
        assert_true("""
        open('%s', write, S),
        write(S, %s),
        close(S).
        """ % (src, term))
        assert term == file_content(src)
    finally:
        delete_file(src)

def test_write_unify():
    src = "__src__"
    term = "X = a"
    create_file(src, "")
    try:
        assert_true("""
        open('%s', write, S),
        write(S, %s),
        close(S).
        """ % (src, term))
    finally:
        delete_file(src)

def test_write_term():
    src = "__src__"
    try:
        assert_true("""
        open('%s', write, S),
        write_term(S, f(g(h(c))), [max_depth(1)]),
        close(S).
        """ % src)
        assert "f(...)" == file_content(src)
    finally:
        delete_file(src)

    try:
        assert_true("""
        open('%s', write, S),
        write_term(S, f(g(h(c))), [max_depth(0)]),
        close(S).
        """ % src)
        assert "f(g(h(c)))" == file_content(src)
    finally:
        delete_file(src)

def test_read():
    src = "__src__"
    create_file(src, "f(a). b. g(d(x)).")
    try:
        assert_true("""
        open('%s', read, S),
        read(S, X), X = f(a),
        read(S, Y), Y = b,
        read(S, Z), Z = g(d(x)),
        close(S).
        """ % src)
    finally:
        delete_file(src)

def test_read_whitespace():
    src = "__src__"
    create_file(src, """
            

    f(a).
        

    """)
    try:
        assert_true("""
        open('%s', read, S),
        read(S, X), X = f(a),
        read(S, Y), Y = end_of_file,
        close(S).
        """ % src)    
    finally:
        delete_file(src)

def test_read_eof_error():
    src = "__src__"
    create_file(src, "f(a)")
    try:
        prolog_raises("syntax_error(E)", """
        open('%s', read, S),
        read(S, X)
        """ % src)
    finally:
        delete_file(src)

def test_read_comment_1():
    src = "__src__"
    create_file(src, "  % asd  ")
    try:
        assert_true("""
        open('%s', read, S),
        read(S, end_of_file),
        close(S).
        """ % src)
    finally:
        delete_file(src)

def test_read_comment_2():
    src = "__src__"
    create_file(src, """
    f(a).%f(b).
    g(x).
    """)
    try:
        assert_true("""
        open('%s', read, S),
        read(S, X), X = f(a),
        read(S, Y), Y = g(x),
        close(S).
        """ % src)
    finally: 
        delete_file(src)

def test_read_current_stream():
    src = "__src__"
    create_file(src, """
    f(a).
    """)
    try:
        assert_true("""
        open('%s', read, S),
        set_input(S),
        read(X), X = f(a),
        close(S).
        """ % src)
    finally:
        delete_file(src)

def test_see_with_file():
    src = "__src__"
    create_file(src, "abc")
    try:
        assert_true("""
        see('%s'),
        get_char(a), get_char(b), get_char(c).
        """ % src)
    finally:
        delete_file(src)

def test_see_with_alias():
    src = "__src__"
    create_file(src, "abc")
    try:
        assert_true("""
        open('%s', read, S, [alias(xxx)]),
        see(xxx),
        get_char(a), get_char(b), get_char(c).
        """ % src)
    finally:
        delete_file(src)

def test_see_errors():
    prolog_raises("type_error(X, Y)", "see(f(a))")
    prolog_raises("instantiation_error", "see(X)")

def test_seen():
    src = "__src__"
    create_file(src, "asdasd")
    try:
        e = Engine()
        w = e.streamwrapper
        assert_true("open('%s', read, S), set_input(S)." % src, e)
        assert len(w.streams) == 3
        assert len(w.aliases) == 3
        assert w.current_instream.fd() not in [0, 1]
        assert_true("seen.", e)
        assert len(w.streams) == 2
        assert len(w.aliases) == 2
        assert w.current_instream.fd() == 0
    finally:
        delete_file(src)

def test_append():
    src = "__src__"
    create_file(src, "a")
    try:
        assert_true("""
        open('%s', append, S),
        put_char(S, a), put_char(S, 'ü'), put_char(S, '¼'),
        close(S).
        """ % src)
        assert file_content(src) == "aaü¼"
    finally:
        delete_file(src)

    create_file(src, "")
    try:
        assert_true("""
        open('%s', append, S),
        put_byte(S, 97), put_byte(S, 98), put_byte(S, 99),
        close(S).
        """ % src)
        assert file_content(src) == "abc"
    finally:
        delete_file(src)

    try:
        assert_true("""
        open('%s', append, S),
        put_char(S, a),
        close(S).
        """ % src)
        assert file_content(src) == "a"
    finally:
        delete_file(src)

    term = "f(a, b, c)"
    try:
        assert_true("""
        open('%s', append, S),
        write(S, %s),
        close(S).
        """ % (src, term))
        assert file_content(src) == term
    finally:
        delete_file(src)

def test_open_stream_strange_buffering():
    prolog_raises("domain_error(buffering, _)",
            "open(blub, write, _, [buffer(strange_stuff)])")

def test_strip():
    assert _strip("abc") == "abc"
    assert _strip("") == ""
    assert _strip(" \n \r \t   abc  \n  \r  \t  ") == "abc"
    assert _strip("    \n    \t   \n   ") == ""

def test_open_with_options():
    m = "mod"
    create_file(m, """
    :- module(%s, []).
    """ % s)
    try:
        prolog_raises("domain_error(stream_option, _)", "open(%s, read, _, [g, 1, a, f(a)])" % m)
        prolog_raises("instantiation_error", "open(%s, read, _, [f(a), X])" % m)
        assert_true("open(%s, read, _, [])." % m)
        assert_true("open(%s, read, _, [a, f(a), []])." % m)
        assert_true("open(%s, read, _, [a, f(a), g(X)])." % m)
    finally:
        delete_file(m)

def test_open_with_options():
    m = "mod"
    create_file(m, """
    :- module(%s, []).
    """ % m)
    try:
        prolog_raises("domain_error(stream_option, _)", "open(%s, read, _, [g, 1, a, f(a)])" % m)
        prolog_raises("instantiation_error", "open(%s, read, _, [f(a), X])" % m)
        assert_true("open(%s, read, _, [])." % m)
        assert_true("open(%s, read, _, [a, f(a), []])." % m)
        assert_true("open(%s, read, _, [a, f(a), []])." % m)
    finally:
        delete_file(m)
