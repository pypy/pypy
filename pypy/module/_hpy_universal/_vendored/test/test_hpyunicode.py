# -*- encoding: utf-8 -*-

from .support import HPyTest

class TestUnicode(HPyTest):

    def test_Check(self):
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                if (HPyUnicode_Check(ctx, arg))
                    return HPy_Dup(ctx, ctx->h_True);
                return HPy_Dup(ctx, ctx->h_False);
            }
            @EXPORT f HPy_METH_O
            @INIT
        """)
        class MyUnicode(str):
            pass

        assert mod.f('hello') is True
        assert mod.f(b'hello') is False
        assert mod.f(MyUnicode('hello')) is True

    def test_FromString(self):
        mod = self.make_module("""
            HPy_DEF_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPyUnicode_FromString(ctx, "foobar");
            }
            @EXPORT f HPy_METH_NOARGS
            @INIT
        """)
        assert mod.f() == "foobar"

    def test_FromWideChar(self):
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                const wchar_t *buf = L"hell\xf2 world";
                long n = HPyLong_AsLong(ctx, arg);
                return HPyUnicode_FromWideChar(ctx, buf, n);
            }
            @EXPORT f HPy_METH_O
            @INIT
        """)
        assert mod.f(-1) == "hellò world"
        assert mod.f(11) == "hellò world"
        assert mod.f(5) == "hellò"


    def test_AsUTF8String(self):
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                return HPyUnicode_AsUTF8String(ctx, arg);
            }
            @EXPORT f HPy_METH_O
            @INIT
        """)
        s = 'hellò'
        b = mod.f(s)
        assert type(b) is bytes
        assert b == s.encode('utf-8')
