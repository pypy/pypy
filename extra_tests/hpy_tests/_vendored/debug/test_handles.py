from test.support import HPyDebugTest

class TestHandles(HPyDebugTest):

    def test_debug_ctx_name(self):
        # this is very similar to the one in test_00_basic, but:
        #   1. by doing the same here, we ensure that we are actually using
        #      the debug ctx in these tests
        #   2. in pypy we run HPyTest with only hpy_abi==universal, so this
        #      tests something which is NOT tested by test_00_basic
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_NOARGS)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPyUnicode_FromString(ctx, ctx->name);
            }

            @EXPORT(f)
            @INIT
        """)
        ctx_name = mod.f()
        assert ctx_name.startswith('HPy Debug Mode ABI')

    def test_get_open_handles(self):
        from hpy.universal import _debug
        mod = self.make_leak_module()
        gen1 = _debug.new_generation()
        mod.leak('hello')
        mod.leak('world')
        gen2 = _debug.new_generation()
        mod.leak('a younger leak')
        leaks1 = _debug.get_open_handles(gen1)
        leaks2 = _debug.get_open_handles(gen2)
        leaks1 = [dh.obj for dh in leaks1]
        leaks2 = [dh.obj for dh in leaks2]
        assert leaks1 == ['a younger leak', 'world', 'hello']
        assert leaks2 == ['a younger leak']

    def test_DebugHandle_id(self):
        from hpy.universal import _debug
        mod = self.make_leak_module()
        gen = _debug.new_generation()
        mod.leak('a')
        mod.leak('b')
        b1, a1 = _debug.get_open_handles(gen)
        b2, a2 = _debug.get_open_handles(gen)
        assert a1.obj == a2.obj == 'a'
        assert b1.obj == b2.obj == 'b'
        #
        assert a1 is not a2
        assert b1 is not b2
        #
        assert a1.id == a2.id
        assert b1.id == b2.id
        assert a1.id != b1.id

    def test_DebugHandle_compare(self):
        import pytest
        from hpy.universal import _debug
        mod = self.make_leak_module()
        gen = _debug.new_generation()
        mod.leak('a')
        mod.leak('a')
        a2, a1 = _debug.get_open_handles(gen)
        assert a1 != a2 # same underlying object, but different DebugHandle
        #
        a2_new, a1_new = _debug.get_open_handles(gen)
        assert a1 is not a1_new  # different objects...
        assert a2 is not a2_new
        assert a1 == a1_new      # ...but same DebugHandle
        assert a2 == a2_new
        #
        with pytest.raises(TypeError):
            a1 < a2
        with pytest.raises(TypeError):
            a1 <= a2
        with pytest.raises(TypeError):
            a1 > a2
        with pytest.raises(TypeError):
            a1 >= a2

        assert not a1 == 'hello'
        assert a1 != 'hello'
        with pytest.raises(TypeError):
            a1 < 'hello'

    def test_DebugHandle_repr(self):
        import pytest
        from hpy.universal import _debug
        mod = self.make_leak_module()
        gen = _debug.new_generation()
        mod.leak('hello')
        h_hello, = _debug.get_open_handles(gen)
        assert repr(h_hello) == "<DebugHandle 0x%x for 'hello'>" % h_hello.id

    def test_LeakDetector(self):
        import pytest
        from hpy.debug import LeakDetector, HPyLeakError
        mod = self.make_leak_module()
        ld = LeakDetector()
        ld.start()
        mod.leak('hello')
        with pytest.raises(HPyLeakError) as exc:
            ld.stop()
        assert str(exc.value).startswith('1 unclosed handle:')
        #
        with pytest.raises(HPyLeakError) as exc:
            with LeakDetector():
                mod.leak('foo')
                mod.leak('bar')
                mod.leak('baz')
        msg = str(exc.value)
        assert msg.startswith('3 unclosed handles:')
        assert 'foo' in msg
        assert 'bar' in msg
        assert 'baz' in msg
        assert 'hello' not in msg
        assert 'world' not in msg
