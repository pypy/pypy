
class AppTestMagic:
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_save_module_content_for_future_reload(self):
        import sys, __pypy__
        d = sys.dont_write_bytecode
        sys.dont_write_bytecode = "hello world"
        __pypy__.save_module_content_for_future_reload(sys)
        sys.dont_write_bytecode = d
        reload(sys)
        assert sys.dont_write_bytecode == "hello world"
        #
        sys.dont_write_bytecode = d
        __pypy__.save_module_content_for_future_reload(sys)

    def test_new_code_hook(self):
        l = []

        def callable(code):
            l.append(code)

        import __pypy__
        __pypy__.set_code_callback(callable)
        d = {}
        try:
            exec """
def f():
    pass
""" in d
        finally:
            __pypy__.set_code_callback(None)
        assert d['f'].__code__ in l

    def test_decode_long(self):
        from __pypy__ import decode_long
        assert decode_long('') == 0
        assert decode_long('\xff\x00') == 255
        assert decode_long('\xff\x7f') == 32767
        assert decode_long('\x00\xff') == -256
        assert decode_long('\x00\x80') == -32768
        assert decode_long('\x80') == -128
        assert decode_long('\x7f') == 127
        assert decode_long('\x55' * 97) == (1 << (97 * 8)) // 3
        assert decode_long('\x00\x80', 'big') == 128
        assert decode_long('\xff\x7f', 'little', False) == 32767
        assert decode_long('\x00\x80', 'little', False) == 32768
        assert decode_long('\x00\x80', 'little', True) == -32768
        raises(ValueError, decode_long, '', 'foo')

    def test_promote(self):
        from __pypy__ import _promote
        assert _promote(1) == 1
        assert _promote(1.1) == 1.1
        assert _promote("abc") == "abc"
        raises(TypeError, _promote, u"abc")
        l = []
        assert _promote(l) is l
        class A(object):
            pass
        a = A()
        assert _promote(a) is a
