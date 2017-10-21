
class AppTestMagic:
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_save_module_content_for_future_reload(self):
        import sys, __pypy__, imp
        d = sys.dont_write_bytecode
        sys.dont_write_bytecode = "hello world"
        __pypy__.save_module_content_for_future_reload(sys)
        sys.dont_write_bytecode = d
        imp.reload(sys)
        assert sys.dont_write_bytecode == "hello world"
        #
        sys.dont_write_bytecode = d
        __pypy__.save_module_content_for_future_reload(sys)

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
