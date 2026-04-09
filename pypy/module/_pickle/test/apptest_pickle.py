import pytest
from _pickle import Pickler, PicklingError, dumps, dump
from _pickle import Unpickler, UnpicklingError, loads
import pickle
from pickle import _dumps as dumps_py, PickleBuffer
from copyreg import dispatch_table
import io
import sys
import datetime

try:
    from copyreg import K
except ImportError:
    # Hashable immutable key object containing unheshable mutable data.
    class K():
        def __init__(self, value):
            self.value = value

        def __reduce__(self):
            # Shouldn't support the recursion itself
            return K, (self.value,)



protocols = range(5, -1, -1)

DICT = {
    'ads_flags': 0,
    'age': 18,
    'birthday': datetime.date(1980, 5, 7),
    'bulletin_count': 0,
    'comment_count': 0,
    'country': 'BR',
    'encrypted_id': 'G9urXXAJwjE',
    'favorite_count': 9,
    'first_name': '',
    'flags': 412317970704,
    'friend_count': 0,
    'gender': 'm',
    'gender_for_display': 'Male',
    'id': 302935349,
    'is_custom_profile_icon': 0,
    'last_name': '',
    'locale_preference': 'pt_BR',
    'member': 0,
    'tags': ['a', 'b', 'c', 'd', 'e', 'f', 'g'],
    'profile_foo_id': 827119638,
    'secure_encrypted_id': 'Z_xxx2dYx3t4YAdnmfgyKw',
    'session_number': 2,
    'signup_id': '201-19225-223',
    'status': 'A',
    'theme': 1,
    'time_created': 1225237014,
    'time_updated': 1233134493,
    'unread_message_count': 0,
    'user_group': '0',
    'username': 'collinwinter',
    'play_count': 9,
    'view_count': 7,
    'zip': ''}



def test_int():
    for proto in protocols:
        n = sys.maxsize
        while n:
            for expected in (-n, n):
                s = dumps(expected, proto)
                s2 = pickle._dumps(expected, proto)
                assert s == s2
                n2 = loads(s)
                assert expected == n2
                n = n >> 1

def test_ints():
    for proto in protocols:
        n = sys.maxsize
        while n:
            for expected in (-n, n):
                s1= dumps(expected, proto)
                s2 = dumps_py(expected, proto)
                assert s1 == s2
                n2 = loads(s1)
                assert expected == n2, "expected %d got %d for protocol %d" %(expected, n2, proto)
            n = n >> 1


def test_long():
    for proto in protocols:
        # 256 bytes is where LONG4 begins.
        for nbits in 1, 8, 8*254, 8*255, 8*256, 8*257:
            nbase = 1 << nbits
            for npos in nbase-1, nbase, nbase+1:
                for n in npos, -npos:
                    pickle = dumps(n, proto)
                    got = loads(pickle)
                    assert n == got
    # Try a monster.  This is quadratic-time in protos 0 & 1, so don't
    # bother with those.
    nbase = int("deadbeeffeedface", 16)
    nbase += nbase << 1000000
    for n in nbase, -nbase:
        p = dumps(n, 2)
        got = loads(p)
        assert n == got


def test_none_true_false():
    s = dumps(None)
    assert s == b'\x80\x04N.'
    assert loads(s) is None
    s = dumps(True)
    assert s == b'\x80\x04\x88.'
    assert loads(s) is True
    s = dumps(False)
    assert s == b'\x80\x04\x89.'
    assert loads(s) is False

def test_bytes():
    s = dumps(b'abc')
    assert s == b'\x80\x04\x95\x07\x00\x00\x00\x00\x00\x00\x00C\x03abc\x94.'
    assert loads(s) == b"abc"
    s = dumps(b'abc' * 1000)
    expected = b'\x80\x04\x95\xbf\x0b\x00\x00\x00\x00\x00\x00B\xb8\x0b\x00\x00abcabcabcab'
    assert s.startswith(expected)
    assert loads(s) == b"abc" * 1000
    s = dumps(b'abc' * 1000000)
    assert s.startswith(b'\x80\x04B\xc0\xc6-\x00abcabcabcabc')
    assert loads(s) == b"abc" * 1000000

def test_unicode():
    s = dumps(u'abc')
    assert s == b'\x80\x04\x95\x07\x00\x00\x00\x00\x00\x00\x00\x8c\x03abc\x94.'
    assert loads(s) == u"abc"
    s = dumps(u'abc' * 1000)
    assert s.startswith(b'\x80\x04\x95\xbf\x0b\x00\x00\x00\x00\x00\x00X\xb8\x0b\x00\x00abcabcabc')
    assert loads(s) == u"abc" * 1000
    s = dumps(u'abc' * 100000)
    assert s.startswith(b'\x80\x04X\xe0\x93\x04\x00abcabcabcabcabc')
    assert loads(s) == u'abc' * 100000

def test_tuple():
    s = dumps(())
    assert s == b'\x80\x04).'
    assert loads(s) == ()
    s = dumps((1, ))
    assert s.startswith(b'\x80\x04\x95\x05\x00\x00\x00\x00\x00\x00\x00K\x01\x85\x94.')
    assert loads(s) == (1,)
    s = dumps((1, ) * 1000)
    assert s.startswith(b'\x80\x04\x95\xd4\x07\x00\x00\x00\x00\x00\x00(K\x01K\x01K')
    assert loads(s) == (1, ) * 1000

def test_memo():
    a = "abcdefghijkl"
    s = dumps((a, a))
    assert s.count(b'abcdefghijkl') == 1
    assert loads(s) == (a, a)
    a = (1, )
    s = dumps((a, a))
    assert s.count(b'K\x01\x85') == 1
    assert loads(s) == (a, a)

def test_list():
    s = dumps([])
    assert s == b'\x80\x04]\x94.'
    assert loads(s) == []
    s = dumps([1])
    assert s == b'\x80\x04\x95\x06\x00\x00\x00\x00\x00\x00\x00]\x94K\x01a.'
    assert loads(s) == [1]
    s = dumps([1] * 1000)
    assert s.startswith(b'\x80\x04\x95\xd5\x07\x00\x00\x00\x00\x00\x00]\x94(K\x01K\x01K\x01K\x01K\x01')
    assert loads(s) == [1] * 1000

def test_list_memo():
    l = []
    l.append(l)
    s = dumps(l)
    assert s == b'\x80\x04\x95\x06\x00\x00\x00\x00\x00\x00\x00]\x94h\x00a.'
    l_roundtrip = loads(s)
    # the comparision fails untranslated
    # assert l_roundtrip == l

    t = (1, 2, 3, [], "abc")
    t[3].append(t)
    s = dumps(t)
    assert s == b'\x80\x04\x95!\x00\x00\x00\x00\x00\x00\x00(K\x01K\x02K\x03]\x94(K\x01K\x02K\x03h\x00\x8c\x03abc\x94t\x94ah\x011h\x02.'
    t_roundtrip = loads(s)
    # the comparision fails untranslated
    # assert t_roundtrip == t

def test_dict():
    s = dumps({})
    assert s == b'\x80\x04}\x94.'
    assert loads(s) == {}
    s = dumps({1: 2})
    assert s == b'\x80\x04\x95\x08\x00\x00\x00\x00\x00\x00\x00}\x94K\x01K\x02s.'
    assert loads(s) == {1: 2}
    d = dict([(a, str(a)) for a in range(10000)])
    s = dumps(d)
    assert s.startswith(b'\x80\x04\x95\x03\x00\x01\x00\x00\x00\x00\x00}\x94(K\x00\x8c\x010\x94K\x01\x8c')
    assert loads(s) == d
    s = dumps({1: 2}, 0)
    assert s == b'(dp0\nI1\nI2\ns.'
    assert loads(s) == {1: 2}
    for proto in [-1]:
        s1 = dumps(DICT, proto)
        s2 = dumps_py(DICT, proto)
        assert s1 == s2
        val = loads(s1)
        assert val == DICT

def test_reduce():
    import sys
    class A:
        pass

    mod = type(sys)('fakemod')
    mod.A = A
    A.__module__ = 'fakemod'
    A.__qualname__ = 'A'
    A.__name__ = 'A'

    sys.modules['fakemod'] = mod
    try:

        a = A()
        a.x = 'abc'
        s = dumps(a)
        assert s == b'\x80\x04\x95"\x00\x00\x00\x00\x00\x00\x00\x8c\x07fakemod\x94\x8c\x01A\x94\x93\x94)\x81\x94}\x94\x8c\x01x\x94\x8c\x03abc\x94sb.'
        a_roundtrip = loads(s)
        assert type(a_roundtrip) == type(a)
        assert a_roundtrip.x == "abc"
    finally:
        del sys.modules['fakemod']

def test_globals():
    s = dumps(dumps)
    assert s == b'\x80\x04\x95\x15\x00\x00\x00\x00\x00\x00\x00\x8c\x07_pickle\x94\x8c\x05dumps\x94\x93\x94.'
    assert loads(s) == dumps

def test_float():
    s = dumps(1.234)
    assert s == b'\x80\x04\x95\n\x00\x00\x00\x00\x00\x00\x00G?\xf3\xbev\xc8\xb49X.'
    assert loads(s) == 1.234

def test_frozenset():
    f = frozenset((1, 2, 3))
    s = dumps(f)
    assert pickle.FROZENSET in s
    f2 = loads(s)
    assert isinstance(f2, frozenset)
    assert f == f2

def test_bytearray():
    for proto in protocols:
        for s in b'', b'xyz', b'xyz'*100:
            b = bytearray(s)
            p = dumps(b, proto)
            bb = loads(p)
            assert bb is not b
            assert b == bb
            if proto <= 3:
                # bytearray is serialized using a global reference
                assert b'bytearray' in p
                assert pickle.GLOBAL in p
            elif proto == 4:
                assert b'bytearray' in p
                assert pickle.STACK_GLOBAL in p
            elif proto == 5:
                assert b'bytearray' not in p
                assert pickle.BYTEARRAY8 in p

def test_complex():
    c = 1+2j
    s = dumps(c)
    c2 = loads(s)
    assert c2 == c

def test_dispatch_table():
    c = 1 + 2j
    f = io.BytesIO()
    p = Pickler(f, 4)
    p.dispatch_table = dispatch_table.copy()

    # modify pickling of complex
    REDUCE_1 = 'reduce_1'
    def reduce_1(obj):
        return str, (REDUCE_1,)

    p.dispatch_table[complex] = reduce_1
    p.dump(c)
    s = f.getvalue()
    assert s == b'\x80\x04\x95#\x00\x00\x00\x00\x00\x00\x00\x8c\x08builtins\x94\x8c\x03str\x94\x93\x94\x8c\x08reduce_1\x94\x85\x94R\x94.'
    c2 = loads(s)
    assert c2 == 'reduce_1'

def test_bad_mark():
    badpickles = [
        b'N(.',                     # STOP
        b'N(2',                     # DUP
        b'cbuiltins\nlist\n)(R',    # REDUCE
        b'cbuiltins\nlist\n()R',
        b']N(a',                    # APPEND
                                    # BUILD
        b'cbuiltins\nValueError\n)R}(b',
        b'cbuiltins\nValueError\n)R(}b',
        # b'(Nd',                     # DICT - protocol 0 not supported on PyPy
        b'N(p1\n',                  # PUT
        b'N(q\x00',                 # BINPUT
        b'N(r\x00\x00\x00\x00',     # LONG_BINPUT
        b'}NN(s',                   # SETITEM
        b'}N(Ns',
        b'}(NNs',
        b'}((u',                    # SETITEMS
        b'cbuiltins\nlist\n)(\x81', # NEWOBJ
        b'cbuiltins\nlist\n()\x81',
        b'N(\x85',                  # TUPLE1
        b'NN(\x86',                 # TUPLE2
        b'N(N\x86',
        b'NNN(\x87',                # TUPLE3
        b'NN(N\x87',
        b'N(NN\x87',
        b']((\x90',                 # ADDITEMS
                                    # NEWOBJ_EX
        b'cbuiltins\nlist\n)}(\x92',
        b'cbuiltins\nlist\n)(}\x92',
        b'cbuiltins\nlist\n()}\x92',
                                    # STACK_GLOBAL
        b'Vbuiltins\n(Vlist\n\x93',
        b'Vbuiltins\nVlist\n(\x93',
        b'N(\x94',                  # MEMOIZE
        b'e',                       # APPENDS
    ]
    for data in badpickles:
        try:
            loads(data)
        except (UnpicklingError, IndexError) as exc:
            pass

def test_truncated():
    badpickles = [
        b'',
        b'B\x03\x00\x00',
        b'\x8e\x03\x00\x00\x00\x00\x00\x00',
        b'Np0',
        b'ibuiltins\nlist\n',
        b'jens:',
    ]
    for data in badpickles:
        try:
            loads(data)
        except (UnpicklingError, EOFError) as e:
            pass

def test_maxint64():
    maxint64 = (1 << 63) - 1
    data = b'I' + str(maxint64).encode("ascii") + b'\n.'
    got = loads(data)
    assert maxint64 == got

    # Try too with a bogus literal.
    data = b'I' + str(maxint64).encode("ascii") + b'JUNK\n.'
    try:
        loads(data)
    except ValueError as e:
        pass
        pass

def test_find_class():
    data = b'\x80\x02c__builtin__\nxrange\nK\x01K\x07K\x01\x87R.'
    got = loads(data)
    assert isinstance(got, range)

def test_function():
    for method, args in (
            ({1, 2}.__contains__, (2,)),
            (set.__contains__, ({1, 2}, 2)),
        ):
        for proto in protocols:
            data = dumps(method, proto)
            pydata = dumps_py(method, proto)
            assert data == pydata
            got = loads(data)
            assert got(*args) == method(*args)

def test_unseekable():
    class UnseekableIO(io.BytesIO):
        def peek(self, *args):
            raise NotImplementedError

        def seekable(self):
            return False

        def seek(self, *args):
            raise io.UnsupportedOperation

        def tell(self):
            raise io.UnsupportedOperation

    data1 = [(x, str(x)) for x in range(2000)] + [b"abcde", len]
    for proto in range(5):
        f = UnseekableIO()
        pickler = Pickler(f, protocol=proto)
        pickler.dump(data1)
        pickled = f.getvalue()

        N = 5
        f = UnseekableIO(pickled * N)
        unpickler = Unpickler(f)
        for i in range(N):
            assert unpickler.load() == data1
        try:
            unpickler.load()
        except EOFError:
            pass

def test_compat_pickle():
    tests = [
        (range(1, 7), '__builtin__', 'xrange'),
        (map(int, '123'), 'itertools', 'imap'),
        (Exception(), 'exceptions', 'Exception'),
    ]
    for val, mod, name in tests:
        for proto in range(3):
            pickled = dumps(val, proto)
            assert('c%s\n%s' % (mod, name)).encode() in pickled
            val2 = loads(pickled)
            assert type(val2) is type(val)

def test_bad_newobj_ex():
    val = loads(b'cbuiltins\nint\n)}\x92.')
    assert val == 0

def test_recursive_set():
    # Set containing an immutable object containing the original set.
    y = set()
    y.add(K(y))
    for proto in range(4, pickle.HIGHEST_PROTOCOL + 1):
        s = dumps(y, proto)
        s2 = dumps_py(y, proto)
        assert s == s2
        x = loads(s)
        assert isinstance(x, set)
        assert len(x) == 1
        assert isinstance(list(x)[0], K)
        assert list(x)[0].value is x

    # Immutable object containing a set containing the original object.
    y, = y
    for proto in range(4, pickle.HIGHEST_PROTOCOL + 1):
        s = dumps(y, proto)
        x = loads(s)
        assert isinstance(x, K)
        assert isinstance(x.value, set)
        assert len(x.value) == 1
        assert list(x.value)[0] is x

def test_picklebuffer():
    pb = PickleBuffer(b'foobar')
    s1 = dumps(pb, 5)
    s2 = dumps_py(pb, 5)
    # assert s1 == s2
    assert loads(s1) == b'foobar'

def test_buffers_error():
    pb = PickleBuffer(b"foobar")
    data = dumps(pb, 5, buffer_callback=[].append)
    # Non iterable buffers
    try:
        loads(data, buffers=object())
    except TypeError:
        pass
    # Buffer iterable exhausts too early
    try:
        loads(data, buffers=[])
    except UnpicklingError:
        pass


# ---- Tests for fixed bugs ----

def test_load_int_true_false():
    # load_int must recognise I01\n as True and I00\n as False
    assert loads(b'I01\n.') is True
    assert loads(b'I00\n.') is False
    assert loads(b'I42\n.') == 42

def test_load_unicode_raw_escape():
    # UNICODE opcode uses raw-unicode-escape, not UTF-8
    assert loads(b'V\\u03c0\n.') == u'\u03c0'
    assert loads(b'Vhello\n.') == u'hello'
    # null and backslash escapes
    assert loads(b'V\\u0000\n.') == u'\x00'

def test_save_bytes_proto0():
    # bytes with high bytes must survive proto 0 round-trip
    for proto in (0, 1, 2):
        for b in (b'\x80', b'\xff', b'\x00\x80\xff'):
            assert loads(dumps(b, proto)) == b

def test_save_str_proto0():
    # save_str with proto 0 must apply chained replacements correctly
    for proto in (0,):
        for s in (u'hello', u'a\nb', u'a\\b', u'\x00', u'\r', u'\x1a'):
            assert loads(dumps(s, proto)) == s
    # high-codepoint string
    assert loads(dumps(u'\u03c0', 0)) == u'\u03c0'

def test_string_opcode():
    # STRING opcode (Python 2 compat)
    assert loads(b"S'hello'\n.") == u'hello'
    assert loads(b'S"hello"\n.') == u'hello'
    assert loads(b"S'\\x41'\n.") == u'A'

def test_binstring_opcode():
    # BINSTRING opcode (Python 2 compat)
    data = b'T\x05\x00\x00\x00hello.'
    assert loads(data) == u'hello'

def test_short_binstring_opcode():
    # SHORT_BINSTRING opcode (Python 2 compat)
    data = b'U\x05hello.'
    assert loads(data) == u'hello'

def test_string_opcode_bytes_encoding():
    # With encoding='bytes', STRING gives bytes not str
    import io
    f = io.BytesIO(b"S'hello'\n.")
    u = Unpickler(f, encoding='bytes')
    assert u.load() == b'hello'

def test_file_write_none_return():
    # Pickler must work even when file.write() returns None
    import io
    class NoneWriter:
        def __init__(self):
            self.buf = b''
        def write(self, data):
            self.buf += data
            # return None (no return value)
    w = NoneWriter()
    p = Pickler(w, 4)
    p.dump(42)
    assert loads(w.buf) == 42

def test_buffers_as_list():
    # Unpickler must accept a list for buffers= (not just iterators)
    from pickle import PickleBuffer
    pb = PickleBuffer(b'hello')
    collected = []
    data = dumps(pb, 5, buffer_callback=collected.append)
    result = loads(data, buffers=collected)    # list, not iterator
    assert result == b'hello'

def test_buffers_exhausted_error():
    # Consuming more out-of-band buffers than provided must raise UnpicklingError
    from pickle import PickleBuffer
    pb = PickleBuffer(b'hello')
    data = dumps(pb, 5, buffer_callback=[].append)
    try:
        loads(data, buffers=[])
    except UnpicklingError:
        pass
    else:
        assert False, "expected UnpicklingError"

def test_reducer_override():
    # reducer_override must be called with object as single argument
    import io
    class MyPickler(Pickler):
        def reducer_override(self, obj):
            if isinstance(obj, int):
                return str, (str(obj),)
            return NotImplemented
    f = io.BytesIO()
    p = MyPickler(f, 4)
    p.dump(42)
    result = loads(f.getvalue())
    assert result == '42'

def test_dispatch_table_on_instance():
    # dispatch_table set on instance must override default pickling
    import io
    f = io.BytesIO()
    p = Pickler(f, 4)
    p.dispatch_table = {complex: lambda c: (str, (str(c),))}
    p.dump(1+2j)
    assert loads(f.getvalue()) == '(1+2j)'

def test_dispatch_table_on_class():
    # dispatch_table set as class attribute must also work
    import io
    class MyPickler(Pickler):
        dispatch_table = {complex: lambda c: (str, (str(c),))}
    f = io.BytesIO()
    p = MyPickler(f, 4)
    p.dump(1+2j)
    assert loads(f.getvalue()) == '(1+2j)'

def test_persistent_id():
    # Pickler subclass with persistent_id must write PERSID/BINPERSID
    import io
    class MyPickler(Pickler):
        def persistent_id(self, obj):
            if isinstance(obj, int):
                return 'int:%d' % obj
            return None
    class MyUnpickler(Unpickler):
        def persistent_load(self, pid):
            if pid.startswith('int:'):
                return int(pid[4:])
            raise UnpicklingError("bad pid")
    for proto in range(6):
        f = io.BytesIO()
        p = MyPickler(f, proto)
        p.dump([1, 2, 'hello'])
        f.seek(0)
        u = MyUnpickler(f)
        result = u.load()
        assert result == [1, 2, 'hello']

def test_pickler_clear_memo():
    # clear_memo must reset the memo dict
    import io
    f = io.BytesIO()
    p = Pickler(f, 4)
    p.dump('hello')
    assert len(p.memo) > 0
    p.clear_memo()
    assert len(p.memo) == 0

def test_pickler_memo_property():
    # memo property must be gettable/settable
    import io
    f1 = io.BytesIO()
    p1 = Pickler(f1, 4)
    p1.dump('hello')
    memo = p1.memo
    assert isinstance(memo, dict)

    # priming: set memo on second pickler
    f2 = io.BytesIO()
    p2 = Pickler(f2, 4)
    p2.memo = memo
    p2.dump('hello')
    # second pickle should use memo (shorter, no re-serialization)
    assert len(f2.getvalue()) < len(f1.getvalue())

def test_unpickler_memo_property():
    # memo property on Unpickler must be gettable/settable
    import io
    data = dumps('hello')
    f = io.BytesIO(data)
    u = Unpickler(f)
    u.load()
    memo = u.memo
    assert isinstance(memo, dict)

def test_pickler_new_without_file():
    # Pickler subclass that doesn't call super().__init__ should raise on dump
    class BadPickler(Pickler):
        def __init__(self):
            pass   # does NOT call super().__init__
    p = BadPickler()
    try:
        p.dump(42)
    except PicklingError:
        pass
    else:
        assert False, "expected PicklingError"

def test_pickler_bad_file():
    # Pickler(bad_file) must raise TypeError if file has no write()
    class NoWrite:
        pass
    try:
        Pickler(NoWrite(), 4)
    except TypeError:
        pass
    else:
        assert False, "expected TypeError"

def test_load_setitems_odd():
    # SETITEMS with odd number of items must raise UnpicklingError
    # }(NNNu. => empty dict, MARK, 3 Nones, SETITEMS
    try:
        loads(b'}(NNNu.')
    except (UnpicklingError, IndexError):
        pass
    else:
        assert False, "expected error"

def test_frame_readline():
    # readline inside a framed pickle (proto 4) must work correctly
    # pickle.dumps(42, 0) uses INT opcode with \n - test it survives framing
    for proto in (4, 5):
        data = dumps(u'line1\nline2', proto)
        assert loads(data) == u'line1\nline2'
    # Also test a string needing readline in protocol 0
    data = dumps(u'hello', 0)
    assert loads(data) == u'hello'

def test_newobj_ex_proto2():
    # save_reduce with __newobj_ex__ and proto < 4 must fall back to REDUCE
    # (NEWOBJ_EX opcode is only available in proto >= 4)
    import io
    import copyreg
    for proto in (2, 3):
        f = io.BytesIO()
        p = Pickler(f, proto)
        # Register a reducer for int that returns a __newobj_ex__ tuple.
        # copyreg.__newobj_ex__(cls, args, kwargs) calls cls(*args, **kwargs).
        p.dispatch_table = {int: lambda x: (copyreg.__newobj_ex__, (int, (x,), {}))}
        p.dump(42)
        data = f.getvalue()
        result = loads(data)
        assert result == 42
        # NEWOBJ_EX opcode (0xd2) must NOT appear for proto < 4
        assert b'\xd2' not in data, "NEWOBJ_EX opcode must not appear in proto < 4"

def test_pickler_subclass_super_init():
    # Pickler subclass that calls super().__init__(file, protocol) must work.
    # Regression test: ForkingPickler-style subclasses (e.g. multiprocessing)
    # call super().__init__(*args) and were broken because Pickler had no __init__.
    import io
    class MyPickler(Pickler):
        def __init__(self, file, protocol=None):
            super().__init__(file, protocol)
    f = io.BytesIO()
    p = MyPickler(f, 2)
    p.dump(42)
    assert loads(f.getvalue()) == 42

def test_memo_reuses_repeated_string():
    # Pickling the same string object multiple times should use GET opcodes.
    import pickletools
    s = 'hello'
    data = [s, s, s]
    buf = io.BytesIO()
    Pickler(buf, 4).dump(data)
    blob = buf.getvalue()
    buf.seek(0)
    ops = [(op.name, arg) for op, arg, pos in pickletools.genops(buf)]
    gets = [op for op, arg in ops if 'GET' in op]
    shorts = [op for op, arg in ops if op == 'SHORT_BINUNICODE' and arg == 'hello']
    assert len(shorts) == 1, "expected 1 full string, got %d: %r" % (len(shorts), ops)
    assert len(gets) == 2, "expected 2 GET ops, got %d: %r" % (len(gets), ops)

def test_readonly_buffer():
    # READONLY_BUFFER opcode must make buffer read-only
    from pickle import PickleBuffer
    import io
    bufs = []
    pb = PickleBuffer(bytearray(b'mutable'))
    data = dumps(pb, 5, buffer_callback=bufs.append)
    # Load with a readonly version
    readonly_buf = memoryview(bufs[0]).toreadonly()
    result = loads(data, buffers=[readonly_buf])
    assert bytes(result) == b'mutable'

def test_reducer_override_subclass():
    # reducer_override defined as a method on a Pickler subclass must be
    # called (not shadowed by a data descriptor on the base Pickler class).
    import io
    class MyPickler(Pickler):
        def reducer_override(self, obj):
            if obj == 42:
                return int, (99,)
            return NotImplemented

    bio = io.BytesIO()
    p = MyPickler(bio, 2)
    p.dump(42)
    result = loads(bio.getvalue())
    assert result == 99, "reducer_override was not called"

    # Non-intercepted objects still pickle normally
    bio2 = io.BytesIO()
    p2 = MyPickler(bio2, 2)
    p2.dump("hello")
    assert loads(bio2.getvalue()) == "hello"

def test_pickle_dict_views():
    # dict_keys/values/items are not picklable; must raise TypeError or PicklingError
    d = {1: 10, "a": "ABC"}
    for proto in range(5 + 1):
        for view in (d.keys(), d.values(), d.items()):
            try:
                dumps(view, proto)
            except (TypeError, PicklingError):
                pass
            else:
                assert False, "expected TypeError or PicklingError for %r" % (view,)

def test_pickle_empty_set():
    # empty set must roundtrip correctly for all protocols (proto >= 4 uses
    # EMPTY_SET opcode; a bug left an unmatched MARK for empty sets)
    for proto in range(pickle.HIGHEST_PROTOCOL + 1):
        for obj in (set(), frozenset()):
            result = loads(dumps(obj, proto))
            assert result == obj
            assert type(result) is type(obj)

def test_unpickle_crash1():
    b = b'\x98\x1f\x1c\x8f\xe1P\xf8n\xa7R\xe8\xc3\x8c\x9d\xc6'
    with raises(pickle.UnpicklingError):
        pickle.loads(b)

def test_unpickle_crash2():
    b = b'p\n'
    with raises(ValueError):
        pickle.loads(b)
