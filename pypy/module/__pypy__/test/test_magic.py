
class AppTestMagic:
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_new_code_hook(self):
        # workaround for running on top of old CPython 2.7 versions
        def exec_(code, d):
            exec(code, d)

        l = []

        def callable(code):
            l.append(code)

        import __pypy__
        __pypy__.set_code_callback(callable)
        d = {}
        try:
            exec_("""
def f():
    pass
""", d)
        finally:
            __pypy__.set_code_callback(None)
        assert d['f'].__code__ in l

    def test_decode_long(self):
        from __pypy__ import decode_long
        assert decode_long(b'') == 0
        assert decode_long(b'\xff\x00') == 255
        assert decode_long(b'\xff\x7f') == 32767
        assert decode_long(b'\x00\xff') == -256
        assert decode_long(b'\x00\x80') == -32768
        assert decode_long(b'\x80') == -128
        assert decode_long(b'\x7f') == 127
        assert decode_long(b'\x55' * 97) == (1 << (97 * 8)) // 3
        assert decode_long(b'\x00\x80', 'big') == 128
        assert decode_long(b'\xff\x7f', 'little', False) == 32767
        assert decode_long(b'\x00\x80', 'little', False) == 32768
        assert decode_long(b'\x00\x80', 'little', True) == -32768
        raises(ValueError, decode_long, b'', 'foo')

    def test_promote(self):
        from __pypy__ import _promote
        assert _promote(1) == 1
        assert _promote(1.1) == 1.1
        assert _promote(b"abc") == b"abc"
        raises(TypeError, _promote, u"abc")
        l = []
        assert _promote(l) is l
        class A(object):
            pass
        a = A()
        assert _promote(a) is a

    def test_set_exc_info(self):
        from __pypy__ import set_exc_info
        terr = TypeError("hello world")
        set_exc_info(TypeError, terr)
        try:
            raise ValueError
        except ValueError as e:
            assert e.__context__ is terr

    def test_set_exc_info_issue3096(self):
        from __pypy__ import set_exc_info
        def recover():
            set_exc_info(None, None)
        def main():
            try:
                raise RuntimeError('aaa')
            finally:
                recover()
                raise RuntimeError('bbb')
        try:
            main()
        except RuntimeError as e:
            assert e.__cause__ is None
            assert e.__context__ is None

    def test_set_exc_info_traceback(self):
        import sys
        from __pypy__ import set_exc_info
        def f():
            1 // 0
        def g():
            try:
                f()
            except ZeroDivisionError:
                return sys.exc_info()[2]
        tb = g()
        terr = TypeError("hello world")
        set_exc_info(TypeError, terr, tb)
        assert sys.exc_info()[2] is tb
