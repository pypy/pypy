# -*- encoding: utf-8 -*-
import itertools
import re
import sys

import pytest

from .support import HPyTest

class TestUnicode(HPyTest):

    def test_Check(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                if (HPyUnicode_Check(ctx, arg))
                    return HPy_Dup(ctx, ctx->h_True);
                return HPy_Dup(ctx, ctx->h_False);
            }
            @EXPORT(f)
            @INIT
        """)
        class MyUnicode(str):
            pass

        assert mod.f('hello') is True
        assert mod.f(b'hello') is False
        assert mod.f(MyUnicode('hello')) is True

    def test_FromString(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                return HPyUnicode_FromString(ctx, "foobar");
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == "foobar"

    def test_FromWideChar(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                const wchar_t buf[] = { 'h', 'e', 'l', 'l', 0xf2, ' ',
                                        'w', 'o', 'r', 'l', 'd', 0 };
                long n = HPyLong_AsLong(ctx, arg);
                return HPyUnicode_FromWideChar(ctx, buf, n);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(-1) == "hellò world"
        assert mod.f(11) == "hellò world"
        assert mod.f(5) == "hellò"


    def test_AsUTF8String(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPyUnicode_AsUTF8String(ctx, arg);
            }
            @EXPORT(f)
            @INIT
        """)
        s = 'hellò'
        b = mod.f(s)
        assert type(b) is bytes
        assert b == s.encode('utf-8')

    def test_AsASCIIString(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPyUnicode_AsASCIIString(ctx, arg);
            }
            @EXPORT(f)
            @INIT
        """)
        s = 'world'
        b = mod.f(s)
        assert type(b) is bytes
        assert b == s.encode('ascii')

    def test_AsLatin1String(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPyUnicode_AsLatin1String(ctx, arg);
            }
            @EXPORT(f)
            @INIT
        """)
        s = "Müller"
        b = mod.f(s)
        assert type(b) is bytes
        assert b == s.encode('latin1')

    def test_AsUTF8AndSize(self):
        mod = self.make_module("""
            #include <string.h>

            static HPy as_utf8_and_size(HPyContext *ctx, HPy arg, HPy_ssize_t *size)
            {
                HPy_ssize_t n;
                const char* buf = HPyUnicode_AsUTF8AndSize(ctx, arg, size);
                long res = 0;

                if (size)
                    n = *size;
                else
                    n = strlen(buf);

                for(int i=0; i<n; i++)
                    res = (res * 10) + buf[i];
                return HPyLong_FromLong(ctx, res);
            }

            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy_ssize_t n;
                return as_utf8_and_size(ctx, arg, &n);
            }

            HPyDef_METH(g, "g", HPyFunc_O)
            static HPy g_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return as_utf8_and_size(ctx, arg, NULL);
            }
            @EXPORT(f)
            @EXPORT(g)
            @INIT
        """)
        assert mod.f('ABC') == 100*ord('A') + 10*ord('B') + ord('C')
        assert mod.f(b'A\0C'.decode('utf-8')) == 100*ord('A') + ord('C')
        assert mod.g('ABC') == 100*ord('A') + 10*ord('B') + ord('C')
        assert mod.g(b'A'.decode('utf-8')) == ord('A')
        assert mod.g(b'A\0'.decode('utf-8')) == ord('A')

    def test_DecodeLatin1(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                const char* buf = HPyBytes_AS_STRING(ctx, arg);
                HPy_ssize_t n = HPyBytes_Size(ctx, arg);
                return HPyUnicode_DecodeLatin1(ctx, buf, n, "");
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(b'M\xfcller') == "Müller"

    def test_DecodeASCII(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                const char* buf = HPyBytes_AS_STRING(ctx, arg);
                HPy_ssize_t n = HPyBytes_Size(ctx, arg);
                return HPyUnicode_DecodeASCII(ctx, buf, n, "");
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(b'hello') == "hello"

    def test_ReadChar(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                long c = HPyUnicode_ReadChar(ctx, arg, 1);
                return HPyLong_FromLong(ctx, c);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f('ABC') == 66

    def test_EncodeFSDefault(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPyUnicode_EncodeFSDefault(ctx, arg);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f('ABC') == b'ABC'

    def test_DecodeFSDefault(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy_ssize_t n;
                const char* buf = HPyUnicode_AsUTF8AndSize(ctx, arg, &n);
                return HPyUnicode_DecodeFSDefault(ctx, buf);
            }

            HPyDef_METH(g, "g", HPyFunc_NOARGS)
            static HPy g_impl(HPyContext *ctx, HPy self)
            {
                const char buf[5] = { 'a', 'b', '\\0', 'c' };
                return HPyUnicode_DecodeFSDefaultAndSize(ctx, buf, 4);
            }

            @EXPORT(f)
            @EXPORT(g)
            @INIT
        """)
        assert mod.f('ABC') == "ABC"
        assert mod.g().encode('ascii') == b'ab\0c'

    def test_FromFormat(self, hpy_abi):
        # Later we generate an HPy function for each case described below:
        # Most of the test cases are taken from CPython:Modules/_testcapi/unicode.c
        # Future work can improve this to add tests from Lib/test/test_capi/test_unicode.py
        cases = [
            # Unrecognized
            (    "%y%d", (SystemError, "invalid format string"), "'w', 42"),
            ("%04.2y%d", (SystemError, "invalid format string"), "'w', 42"),
            ("%u %? %u", (SystemError, "invalid format string"), "1, 2"),

            # "%%" (options are rejected)
            (  "%%", "%", "0"),
            ("%%%c", "%w", "'w'"),
            ( "%0%", (SystemError, "invalid format string"), "0"),
            ("%00%", (SystemError, "invalid format string"), "0"),
            ( "%2%", (SystemError, "invalid format string"), "0"),
            ("%02%", (SystemError, "invalid format string"), "0"),
            ("%.0%", (SystemError, "invalid format string"), "0"),
            ("%.2%", (SystemError, "invalid format string"), "0"),

            # "%c"
            (  "%c", "c", "'c'"),

            # Integers
            ("%d",            "123",               '(int)123'),
            ("%i",            "123",               '(int)123'),
            ("%u",            "123",      '(unsigned int)123'),
            ("%ld",           "123",              '(long)123'),
            ("%li",           "123",              '(long)123'),
            ("%lu",           "123",     '(unsigned long)123'),
            ("%lld",          "123",         '(long long)123'),
            ("%lli",          "123",         '(long long)123'),
            ("%llu",          "123",'(unsigned long long)123'),
            ("%zd",           "123",       '(HPy_ssize_t)123'),
            ("%zi",           "123",       '(HPy_ssize_t)123'),
            ("%zu",           "123",            '(size_t)123'),
            ("%x",             "7b",               '(int)123'),

            ("%d",           "-123",              '(int)-123'),
            ("%i",           "-123",              '(int)-123'),
            ("%ld",          "-123",             '(long)-123'),
            ("%li",          "-123",             '(long)-123'),
            ("%lld",         "-123",        '(long long)-123'),
            ("%lli",         "-123",        '(long long)-123'),
            ("%zd",          "-123",      '(HPy_ssize_t)-123'),
            ("%zi",          "-123",      '(HPy_ssize_t)-123'),
            ("%x",       "ffffff85",              '(int)-123'),

            # Integers: width < length
            ("%1d",           "123",               '(int)123'),
            ("%1i",           "123",               '(int)123'),
            ("%1u",           "123",      '(unsigned int)123'),
            ("%1ld",          "123",              '(long)123'),
            ("%1li",          "123",              '(long)123'),
            ("%1lu",          "123",     '(unsigned long)123'),
            ("%1lld",         "123",         '(long long)123'),
            ("%1lli",         "123",         '(long long)123'),
            ("%1llu",         "123",'(unsigned long long)123'),
            ("%1zd",          "123",       '(HPy_ssize_t)123'),
            ("%1zi",          "123",       '(HPy_ssize_t)123'),
            ("%1zu",          "123",            '(size_t)123'),
            ("%1x",            "7b",               '(int)123'),

            ("%1d",          "-123",              '(int)-123'),
            ("%1i",          "-123",              '(int)-123'),
            ("%1ld",         "-123",             '(long)-123'),
            ("%1li",         "-123",             '(long)-123'),
            ("%1lld",        "-123",        '(long long)-123'),
            ("%1lli",        "-123",        '(long long)-123'),
            ("%1zd",         "-123",      '(HPy_ssize_t)-123'),
            ("%1zi",         "-123",      '(HPy_ssize_t)-123'),
            ("%1x",      "ffffff85",              '(int)-123'),

            # Integers: width > length
            ("%5d",         "  123",               '(int)123'),
            ("%5i",         "  123",               '(int)123'),
            ("%5u",         "  123",      '(unsigned int)123'),
            ("%5ld",        "  123",              '(long)123'),
            ("%5li",        "  123",              '(long)123'),
            ("%5lu",        "  123",     '(unsigned long)123'),
            ("%5lld",       "  123",         '(long long)123'),
            ("%5lli",       "  123",         '(long long)123'),
            ("%5llu",       "  123",'(unsigned long long)123'),
            ("%5zd",        "  123",       '(HPy_ssize_t)123'),
            ("%5zi",        "  123",       '(HPy_ssize_t)123'),
            ("%5zu",        "  123",            '(size_t)123'),
            ("%5x",         "   7b",               '(int)123'),

            ("%5d",         " -123",              '(int)-123'),
            ("%5i",         " -123",              '(int)-123'),
            ("%5ld",        " -123",             '(long)-123'),
            ("%5li",        " -123",             '(long)-123'),
            ("%5lld",       " -123",        '(long long)-123'),
            ("%5lli",       " -123",        '(long long)-123'),
            ("%5zd",        " -123",      '(HPy_ssize_t)-123'),
            ("%5zi",        " -123",      '(HPy_ssize_t)-123'),
            ("%9x",     " ffffff85",              '(int)-123'),

            # Integers: width > length, 0-flag
            ("%05d",        "00123",               '(int)123'),
            ("%05i",        "00123",               '(int)123'),
            ("%05u",        "00123",      '(unsigned int)123'),
            ("%05ld",       "00123",              '(long)123'),
            ("%05li",       "00123",              '(long)123'),
            ("%05lu",       "00123",     '(unsigned long)123'),
            ("%05lld",      "00123",         '(long long)123'),
            ("%05lli",      "00123",         '(long long)123'),
            ("%05llu",      "00123",'(unsigned long long)123'),
            ("%05zd",       "00123",       '(HPy_ssize_t)123'),
            ("%05zi",       "00123",       '(HPy_ssize_t)123'),
            ("%05zu",       "00123",            '(size_t)123'),
            ("%05x",        "0007b",               '(int)123'),

            ("%05d",        "-0123",              '(int)-123'),
            ("%05i",        "-0123",              '(int)-123'),
            ("%05ld",       "-0123",             '(long)-123'),
            ("%05li",       "-0123",             '(long)-123'),
            ("%05lld",      "-0123",        '(long long)-123'),
            ("%05lli",      "-0123",        '(long long)-123'),
            ("%05zd",       "-0123",      '(HPy_ssize_t)-123'),
            ("%05zi",       "-0123",      '(HPy_ssize_t)-123'),
            ("%09x",    "0ffffff85",              '(int)-123'),

            # Integers: precision < length
            ("%.1d",          "123",               '(int)123'),
            ("%.1i",          "123",               '(int)123'),
            ("%.1u",          "123",      '(unsigned int)123'),
            ("%.1ld",         "123",              '(long)123'),
            ("%.1li",         "123",              '(long)123'),
            ("%.1lu",         "123",     '(unsigned long)123'),
            ("%.1lld",        "123",         '(long long)123'),
            ("%.1lli",        "123",         '(long long)123'),
            ("%.1llu",        "123",'(unsigned long long)123'),
            ("%.1zd",         "123",       '(HPy_ssize_t)123'),
            ("%.1zi",         "123",       '(HPy_ssize_t)123'),
            ("%.1zu",         "123",            '(size_t)123'),
            ("%.1x",           "7b",               '(int)123'),

            ("%.1d",         "-123",              '(int)-123'),
            ("%.1i",         "-123",              '(int)-123'),
            ("%.1ld",        "-123",             '(long)-123'),
            ("%.1li",        "-123",             '(long)-123'),
            ("%.1lld",       "-123",        '(long long)-123'),
            ("%.1lli",       "-123",        '(long long)-123'),
            ("%.1zd",        "-123",      '(HPy_ssize_t)-123'),
            ("%.1zi",        "-123",      '(HPy_ssize_t)-123'),
            ("%.1x",     "ffffff85",              '(int)-123'),

            # Integers: precision > length
            ("%.5d",        "00123",               '(int)123'),
            ("%.5i",        "00123",               '(int)123'),
            ("%.5u",        "00123",      '(unsigned int)123'),
            ("%.5ld",       "00123",              '(long)123'),
            ("%.5li",       "00123",              '(long)123'),
            ("%.5lu",       "00123",     '(unsigned long)123'),
            ("%.5lld",      "00123",         '(long long)123'),
            ("%.5lli",      "00123",         '(long long)123'),
            ("%.5llu",      "00123",'(unsigned long long)123'),
            ("%.5zd",       "00123",       '(HPy_ssize_t)123'),
            ("%.5zi",       "00123",       '(HPy_ssize_t)123'),
            ("%.5zu",       "00123",            '(size_t)123'),
            ("%.5x",        "0007b",               '(int)123'),

            ("%.5d",       "-00123",              '(int)-123'),
            ("%.5i",       "-00123",              '(int)-123'),
            ("%.5ld",      "-00123",             '(long)-123'),
            ("%.5li",      "-00123",             '(long)-123'),
            ("%.5lld",     "-00123",        '(long long)-123'),
            ("%.5lli",     "-00123",        '(long long)-123'),
            ("%.5zd",      "-00123",      '(HPy_ssize_t)-123'),
            ("%.5zi",      "-00123",      '(HPy_ssize_t)-123'),
            ("%.9x",    "0ffffff85",              '(int)-123'),

            # Integers: width > precision > length
            ("%7.5d",     "  00123",               '(int)123'),
            ("%7.5i",     "  00123",               '(int)123'),
            ("%7.5u",     "  00123",      '(unsigned int)123'),
            ("%7.5ld",    "  00123",              '(long)123'),
            ("%7.5li",    "  00123",              '(long)123'),
            ("%7.5lu",    "  00123",     '(unsigned long)123'),
            ("%7.5lld",   "  00123",         '(long long)123'),
            ("%7.5lli",   "  00123",         '(long long)123'),
            ("%7.5llu",   "  00123",'(unsigned long long)123'),
            ("%7.5zd",    "  00123",       '(HPy_ssize_t)123'),
            ("%7.5zi",    "  00123",       '(HPy_ssize_t)123'),
            ("%7.5zu",    "  00123",            '(size_t)123'),
            ("%7.5x",     "  0007b",               '(int)123'),

            ("%7.5d",     " -00123",              '(int)-123'),
            ("%7.5i",     " -00123",              '(int)-123'),
            ("%7.5ld",    " -00123",             '(long)-123'),
            ("%7.5li",    " -00123",             '(long)-123'),
            ("%7.5lld",   " -00123",        '(long long)-123'),
            ("%7.5lli",   " -00123",        '(long long)-123'),
            ("%7.5zd",    " -00123",      '(HPy_ssize_t)-123'),
            ("%7.5zi",    " -00123",      '(HPy_ssize_t)-123'),
            ("%10.9x", " 0ffffff85",              '(int)-123'),

            # Integers: width > precision > length, 0-flag
            ("%07.5d",    "0000123",               '(int)123'),
            ("%07.5i",    "0000123",               '(int)123'),
            ("%07.5u",    "0000123",      '(unsigned int)123'),
            ("%07.5ld",   "0000123",              '(long)123'),
            ("%07.5li",   "0000123",              '(long)123'),
            ("%07.5lu",   "0000123",     '(unsigned long)123'),
            ("%07.5lld",  "0000123",         '(long long)123'),
            ("%07.5lli",  "0000123",         '(long long)123'),
            ("%07.5llu",  "0000123",'(unsigned long long)123'),
            ("%07.5zd",   "0000123",       '(HPy_ssize_t)123'),
            ("%07.5zi",   "0000123",       '(HPy_ssize_t)123'),
            ("%07.5zu",   "0000123",            '(size_t)123'),
            ("%07.5x",    "000007b",               '(int)123'),

            ("%07.5d",    "-000123",              '(int)-123'),
            ("%07.5i",    "-000123",              '(int)-123'),
            ("%07.5ld",   "-000123",             '(long)-123'),
            ("%07.5li",   "-000123",             '(long)-123'),
            ("%07.5lld",  "-000123",        '(long long)-123'),
            ("%07.5lli",  "-000123",        '(long long)-123'),
            ("%07.5zd",   "-000123",      '(HPy_ssize_t)-123'),
            ("%07.5zi",   "-000123",      '(HPy_ssize_t)-123'),
            ("%010.9x","00ffffff85",              '(int)-123'),

            # Integers: precision > width > length
            ("%5.7d",     "0000123",               '(int)123'),
            ("%5.7i",     "0000123",               '(int)123'),
            ("%5.7u",     "0000123",      '(unsigned int)123'),
            ("%5.7ld",    "0000123",              '(long)123'),
            ("%5.7li",    "0000123",              '(long)123'),
            ("%5.7lu",    "0000123",     '(unsigned long)123'),
            ("%5.7lld",   "0000123",         '(long long)123'),
            ("%5.7lli",   "0000123",         '(long long)123'),
            ("%5.7llu",   "0000123",'(unsigned long long)123'),
            ("%5.7zd",    "0000123",       '(HPy_ssize_t)123'),
            ("%5.7zi",    "0000123",       '(HPy_ssize_t)123'),
            ("%5.7zu",    "0000123",            '(size_t)123'),
            ("%5.7x",     "000007b",               '(int)123'),

            ("%5.7d",    "-0000123",              '(int)-123'),
            ("%5.7i",    "-0000123",              '(int)-123'),
            ("%5.7ld",   "-0000123",             '(long)-123'),
            ("%5.7li",   "-0000123",             '(long)-123'),
            ("%5.7lld",  "-0000123",        '(long long)-123'),
            ("%5.7lli",  "-0000123",        '(long long)-123'),
            ("%5.7zd",   "-0000123",      '(HPy_ssize_t)-123'),
            ("%5.7zi",   "-0000123",      '(HPy_ssize_t)-123'),
            ("%9.10x", "00ffffff85",              '(int)-123'),

            # Integers: precision > width > length, 0-flag
            ("%05.7d",    "0000123",               '(int)123'),
            ("%05.7i",    "0000123",               '(int)123'),
            ("%05.7u",    "0000123",      '(unsigned int)123'),
            ("%05.7ld",   "0000123",              '(long)123'),
            ("%05.7li",   "0000123",              '(long)123'),
            ("%05.7lu",   "0000123",     '(unsigned long)123'),
            ("%05.7lld",  "0000123",         '(long long)123'),
            ("%05.7lli",  "0000123",         '(long long)123'),
            ("%05.7llu",  "0000123",'(unsigned long long)123'),
            ("%05.7zd",   "0000123",       '(HPy_ssize_t)123'),
            ("%05.7zi",   "0000123",       '(HPy_ssize_t)123'),
            ("%05.7zu",   "0000123",            '(size_t)123'),
            ("%05.7x",    "000007b",               '(int)123'),

            ("%05.7d",   "-0000123",              '(int)-123'),
            ("%05.7i",   "-0000123",              '(int)-123'),
            ("%05.7ld",  "-0000123",             '(long)-123'),
            ("%05.7li",  "-0000123",             '(long)-123'),
            ("%05.7lld", "-0000123",        '(long long)-123'),
            ("%05.7lli", "-0000123",        '(long long)-123'),
            ("%05.7zd",  "-0000123",      '(HPy_ssize_t)-123'),
            ("%05.7zi",  "-0000123",      '(HPy_ssize_t)-123'),
            ("%09.10x","00ffffff85",              '(int)-123'),

            # Integers: precision = 0, arg = 0 (empty string in C)
            ("%.0d",            "0",                 '(int)0'),
            ("%.0i",            "0",                 '(int)0'),
            ("%.0u",            "0",        '(unsigned int)0'),
            ("%.0ld",           "0",                '(long)0'),
            ("%.0li",           "0",                '(long)0'),
            ("%.0lu",           "0",       '(unsigned long)0'),
            ("%.0lld",          "0",           '(long long)0'),
            ("%.0lli",          "0",           '(long long)0'),
            ("%.0llu",          "0",  '(unsigned long long)0'),
            ("%.0zd",           "0",         '(HPy_ssize_t)0'),
            ("%.0zi",           "0",         '(HPy_ssize_t)0'),
            ("%.0zu",           "0",              '(size_t)0'),
            ("%.0x",            "0",                 '(int)0'),

            # Strings
            ("%s",     "None", ' "None"'),
            ("%U",     "None", 'unicode'),
            ("%A",     "None", 'ctx->h_None'),
            ("%S",     "None", 'ctx->h_None'),
            ("%R",     "None", 'ctx->h_None'),
            ("%V",     "None", 'unicode, "ignored"'),
            ("%V",     "None", '   NULL,    "None"'),

            # Strings: width < length
            ("%1s",    "None", ' "None"'),
            ("%1U",    "None", 'unicode'),
            ("%1A",    "None", 'ctx->h_None'),
            ("%1S",    "None", 'ctx->h_None'),
            ("%1R",    "None", 'ctx->h_None'),
            ("%1V",    "None", 'unicode, "ignored"'),
            ("%1V",    "None", '   NULL,    "None"'),

            # Strings: width > length
            ("%5s",   " None", ' "None"'),
            ("%5U",   " None", 'unicode'),
            ("%5A",   " None", 'ctx->h_None'),
            ("%5S",   " None", 'ctx->h_None'),
            ("%5R",   " None", 'ctx->h_None'),
            ("%5V",   " None", 'unicode, "ignored"'),
            ("%5V",   " None", '   NULL,    "None"'),

            # Strings: precision < length
            ("%.1s",      "N", ' "None"'),
            ("%.1U",      "N", 'unicode'),
            ("%.1A",      "N", 'ctx->h_None'),
            ("%.1S",      "N", 'ctx->h_None'),
            ("%.1R",      "N", 'ctx->h_None'),
            ("%.1V",      "N", 'unicode, "ignored"'),
            ("%.1V",      "N", '   NULL,    "None"'),

            # Strings: precision > length
            ("%.5s",   "None", ' "None"'),
            ("%.5U",   "None", 'unicode'),
            ("%.5A",   "None", 'ctx->h_None'),
            ("%.5S",   "None", 'ctx->h_None'),
            ("%.5R",   "None", 'ctx->h_None'),
            ("%.5V",   "None", 'unicode, "ignored"'),
            ("%.5V",   "None", '   NULL,    "None"'),

            # Strings: precision < length, width > length
            ("%5.1s", "    N", ' "None"'),
            ("%5.1U", "    N", 'unicode'),
            ("%5.1A", "    N", 'ctx->h_None'),
            ("%5.1S", "    N", 'ctx->h_None'),
            ("%5.1R", "    N", 'ctx->h_None'),
            ("%5.1V", "    N", 'unicode, "ignored"'),
            ("%5.1V", "    N", '   NULL,    "None"'),

            # Strings: width < length, precision > length
            ("%1.5s",  "None", ' "None"'),
            ("%1.5U",  "None", 'unicode'),
            ("%1.5A",  "None", 'ctx->h_None'),
            ("%1.5S",  "None", 'ctx->h_None'),
            ("%1.5R",  "None", 'ctx->h_None'),
            ("%1.5V",  "None", 'unicode, "ignored"'),
            ("%1.5V",  "None", '   NULL,    "None"'),

            # Additional HPy tests:
            ("%c", (OverflowError, re.escape("character argument not in range(0x110000)")), "0x10ffff + 2"),

            ("check if %5d %s %6.3d is %5S or %6.3S",
             "check if    42 ==   -042 is  True or    Fal",
             '42, "==", -42, ctx->h_True, ctx->h_False')
        ]

        cpython_incompatible_cases = [
            (    "%s", (SystemError, "null c string passed as value for formatting unit '%s'"), "NULL"),

            (   '%4p', (SystemError, "formatting unit '%p' does not support width nor precision"), "0"),
            (  '%04p', (SystemError, "formatting unit '%p' does not support 0-padding"), "0"),
            (  '%.4p', (SystemError, "formatting unit '%p' does not support width nor precision"), "0"),
            ( '%8.4p', (SystemError, "formatting unit '%p' does not support width nor precision"), "0"),
            ('%08.4p', (SystemError, "formatting unit '%p' does not support 0-padding"), "0"),

            (   '%4c', (SystemError, "formatting unit '%c' does not support width nor precision"), "0"),
            (  '%04c', (SystemError, "formatting unit '%c' does not support 0-padding"), "0"),
            (  '%.4c', (SystemError, "formatting unit '%c' does not support width nor precision"), "0"),
            ( '%8.4c', (SystemError, "formatting unit '%c' does not support width nor precision"), "0"),
            ('%08.4c', (SystemError, "formatting unit '%c' does not support 0-padding"), "0"),

            ("%U", (SystemError, ".*HPy_NULL passed.*"), "HPy_NULL"),
            ("%S", (SystemError, ".*HPy_NULL passed.*"), "HPy_NULL"),
            ("%R", (SystemError, ".*HPy_NULL passed.*"), "HPy_NULL"),
            ("%A", (SystemError, ".*HPy_NULL passed.*"), "HPy_NULL"),

            ("%0s", (SystemError, "formatting unit '%s' does not support 0-padding"), "0"),
            ("%0p", (SystemError, "formatting unit '%p' does not support 0-padding"), "0"),
            ("%0U", (SystemError, "formatting unit '%U' does not support 0-padding"), "0"),
            ("%0V", (SystemError, "formatting unit '%V' does not support 0-padding"), "0"),
            ("%0S", (SystemError, "formatting unit '%S' does not support 0-padding"), "0"),
            ("%0R", (SystemError, "formatting unit '%R' does not support 0-padding"), "0"),
            ("%0A", (SystemError, "formatting unit '%A' does not support 0-padding"), "0"),
        ]

        cases += cpython_incompatible_cases
        cpython_incompatible_cases = set(cpython_incompatible_cases)

        # Generate a unique name for each test that is also valid C identifier
        names = ['a' + str(i) for i in range(0, len(cases))]
        cases = {name:case for (name, case) in itertools.zip_longest(names, cases)}

        # ---
        # Generate the test code from the cases:
        def makefun(name, fmt, arg):
            cpy_arg = arg.replace("ctx->h_None", "Py_None").replace("HPy_ssize_t", "Py_ssize_t")
            return """
                HPyDef_METH({name}, "{name}", HPyFunc_NOARGS)
                static HPy {name}_impl(HPyContext *ctx, HPy self)
                {{
                    HPy unicode = HPyUnicode_FromString(ctx, "None");
                    if (HPy_IsNull(unicode)) return HPy_NULL;
                    HPy result = HPyUnicode_FromFormat(ctx, "{fmt}", {arg});
                    HPy_Close(ctx, unicode);
                    return result;
                }}

                #ifdef CPM_WITH_CPYTHON
                HPyDef_METH({name}_cpython, "{name}_cpython", HPyFunc_NOARGS)
                static HPy {name}_cpython_impl(HPyContext *ctx, HPy self)
                {{
                    PyObject *unicode = PyUnicode_FromString("None");
                    PyObject *py = PyUnicode_FromFormat("{fmt}", {cpy_arg});
                    HPy hpy = HPy_NULL;
                    if (py != NULL) {{
                        hpy = HPy_FromPyObject(ctx, py);
                        Py_DECREF(py);
                    }}
                    Py_DECREF(unicode);
                    return hpy;
                }}
                #endif
            """.format(name=name, fmt=fmt, arg=arg, cpy_arg=cpy_arg)

        # Change False->True to also check comparison with CPython.
        # Works only for 3.12 or higher, lower versions have bugs that are
        # fixed in HPy
        compare_with_cpython = False and \
                               hpy_abi == 'cpython' and \
                               sys.implementation.name == 'cpython' and \
                               sys.implementation.version.major >= 3 and \
                               sys.implementation.version.minor >= 12

        # Create functions for each case using the "makefun" template, export them
        lines = ['#define CPM_WITH_CPYTHON'] if compare_with_cpython else []
        lines += [makefun(name, fmt, arg) for (name, (fmt, _, arg)) in cases.items()]
        lines += ["@EXPORT({})".format(name) for name in cases.keys()]
        if compare_with_cpython:
            lines += ["@EXPORT({}_cpython)".format(name) for name in cases.keys()]
        lines += ["@INIT"]

        mod = self.make_module("\n".join(lines))

        def check_cpython_raises_any(name):
            try:
                getattr(mod, name + "_cpython")()
                return False
            except:
                return True

        for (name, case) in cases.items():
            (_, expected, _) = case
            if isinstance(expected, tuple):
                (expected_type, expected_message) = expected
                with pytest.raises(expected_type, match=expected_message):
                    getattr(mod, name)()
                if compare_with_cpython and case not in cpython_incompatible_cases:
                    check_cpython_raises_any(name)
                continue

            assert getattr(mod, name)() == expected, name + ":" + repr(case)
            if compare_with_cpython and case not in cpython_incompatible_cases:
                assert getattr(mod, name)() == getattr(mod, name + "_cpython")(), \
                    "CPython check: " + name + ":" + repr(case)

    def test_FromFormat_Ptr(self):
        # '%p' is platform dependent to some extent, so we need to use regex
        mod = self.make_module("""
            HPyDef_METH(p, "p", HPyFunc_NOARGS)
            static HPy p_impl(HPyContext *ctx, HPy self)
            {
                return HPyUnicode_FromFormat(ctx, "prefix-%p-suffix", (void*) 0xbeef);
            }

            @EXPORT(p)
            @INIT
        """)
        assert re.match(r'prefix-0x[0]{,60}[bB][eE][eE][fF]-suffix', mod.p())

    def test_FromFormat_PyObjs(self):
        mod = self.make_module("""
            HPyDef_METH(S, "S", HPyFunc_O)
            static HPy S_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPyUnicode_FromFormat(ctx, "prefix-%S-suffix", arg);
            }

            HPyDef_METH(R, "R", HPyFunc_O)
            static HPy R_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPyUnicode_FromFormat(ctx, "prefix-%R-suffix", arg);
            }

            HPyDef_METH(A, "A", HPyFunc_O)
            static HPy A_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPyUnicode_FromFormat(ctx, "prefix-%A-suffix", arg);
            }

            @EXPORT(S)
            @EXPORT(R)
            @EXPORT(A)
            @INIT
        """)

        class MyObj:
            def __str__(self):
                return "MyObj.__str__"

            def __repr__(self):
                return "MyObj.__repr__ü"

        assert mod.S('ABC') == 'prefix-ABC-suffix'
        assert mod.S(42) == 'prefix-42-suffix'
        assert mod.S(MyObj()) == 'prefix-MyObj.__str__-suffix'

        assert mod.R('ABC') == "prefix-'ABC'-suffix"
        assert mod.R(42) == 'prefix-42-suffix'
        assert mod.R(MyObj()) == 'prefix-MyObj.__repr__ü-suffix'

        assert mod.A('ABC') == "prefix-'ABC'-suffix"
        assert mod.A(42) == 'prefix-42-suffix'
        assert mod.A(MyObj()) == 'prefix-MyObj.__repr__\\xfc-suffix'

    def test_FromFormat_NoAsciiEncodedFmt(self):
        mod = self.make_module("""
            HPyDef_METH(no_ascii_fmt, "no_ascii_fmt", HPyFunc_O)
            static HPy no_ascii_fmt_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy_ssize_t s;
                const char *fmt = HPyUnicode_AsUTF8AndSize(ctx, arg, &s);
                return HPyUnicode_FromFormat(ctx, fmt);
            }

            @EXPORT(no_ascii_fmt)
            @INIT
        """)

        with pytest.raises(ValueError, match="expected an ASCII-encoded format string, got a non-ASCII byte: 0xc3"):
            mod.no_ascii_fmt("format ü")

    def test_FromFormat_Unicode(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPyUnicode_FromFormat(ctx, "%10.5S", arg);
            }

            @EXPORT(f)
            @INIT
        """)
        assert mod.f("€urΘpe") == "     €urΘp"

    def test_FromFormat_LongFormat(self):
        chunk_size = 1000
        chunks_count = 5
        total_c_size = (chunk_size + 1) * chunks_count + 1
        args = ','.join([str(i) for i in range(1, chunks_count+1)])
        mod = self.make_module("""
            #include <string.h>

            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {{
                const size_t chunk_size = {chunk_size} + 1; // for the '%d'
                const size_t total_size = {total_size};
                char fmt[{total_size}];
                memset(fmt, 'a', total_size);
                fmt[total_size - 1] = '\\0';
                for (size_t i = 0; i < {chunks_count}; i++) {{
                    fmt[i * chunk_size] = '%';
                    fmt[(i * chunk_size)+1] = 'd';
                }}
                return HPyUnicode_FromFormat(ctx, fmt, {args});
            }}

            @EXPORT(f)
            @INIT
        """.format(chunk_size=chunk_size, chunks_count=chunks_count, total_size=total_c_size, args=args))
        assert mod.f() == ''.join([str(i) + ("a" * (chunk_size - 1)) for i in range(1,chunks_count+1)])

    def test_FromFormat_Limits(self):
        import sys
        mod = self.make_module("""
                #include <stdio.h>

                HPyDef_METH(width, "width", HPyFunc_NOARGS)
                static HPy width_impl(HPyContext *ctx, HPy self)
                {{
                    char fmt[512];
                    sprintf(fmt, "%%%llud", ((unsigned long long) HPY_SSIZE_T_MAX) + 1ull);
                    return HPyUnicode_FromFormat(ctx, fmt, 42);
                }}

                HPyDef_METH(precision, "precision", HPyFunc_NOARGS)
                static HPy precision_impl(HPyContext *ctx, HPy self)
                {{
                    char fmt[512];
                    sprintf(fmt, "%%.%llud", ((unsigned long long) HPY_SSIZE_T_MAX) + 1ull);
                    return HPyUnicode_FromFormat(ctx, fmt, 42);
                }}

                HPyDef_METH(memory_err_width, "memory_err_width", HPyFunc_NOARGS)
                static HPy memory_err_width_impl(HPyContext *ctx, HPy self)
                {{
                    return HPyUnicode_FromFormat(ctx, "%{max_size}d", 42);
                }}

                HPyDef_METH(memory_err_precision, "memory_err_precision", HPyFunc_NOARGS)
                static HPy memory_err_precision_impl(HPyContext *ctx, HPy self)
                {{
                    return HPyUnicode_FromFormat(ctx, "%.{max_size}d", 42);
                }}

                @EXPORT(width)
                @EXPORT(precision)
                @INIT
            """.format(max_size = str(sys.maxsize + 1)))
        with pytest.raises(ValueError) as exc:
            mod.width()
        assert str(exc.value) == "width too big"
        with pytest.raises(ValueError) as exc:
            mod.precision()
        assert str(exc.value) == "precision too big"

    def test_FromEncodedObject(self):
        import pytest
        mod = self.make_module("""
            static const char *as_string(HPyContext *ctx, HPy h)
            {
                const char *res = HPyUnicode_AsUTF8AndSize(ctx, h, NULL);
                if (res == NULL)
                    HPyErr_Clear(ctx);
                return res;
            }

            HPyDef_METH(f, "f", HPyFunc_VARARGS)
            static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy h_obj;
                const char *encoding, *errors;
                if (nargs != 3) {
                    HPyErr_SetString(ctx, ctx->h_TypeError, "expected exactly 3 arguments");
                    return HPy_NULL;
                }
                h_obj = HPy_Is(ctx, args[0], ctx->h_None) ? HPy_NULL : args[0];
                encoding = as_string(ctx, args[1]);
                errors = as_string(ctx, args[2]);
                return HPyUnicode_FromEncodedObject(ctx, h_obj, encoding, errors);
            }
            @EXPORT(f)
            @INIT
        """)
        # "hellö" as UTF-8 encoded bytes
        utf8_bytes = b"hell\xc3\xb6"
        # "hellö" as UTF-16 encoded bytes
        utf16_bytes = b'\xff\xfeh\x00e\x00l\x00l\x00\xf6\x00'
        ascii_codepoints = bytes(range(1, 128))

        # note: None (if passed to arguments 'encoding' or 'errors') will be
        # translated to a NULL pointer

        for errors in (None, "strict", "ignore", "replace"):
            assert mod.f(b"hello", "ascii", errors) == "hello"
            assert mod.f(utf8_bytes, "utf8", errors) == "hellö"
            assert mod.f(utf16_bytes, "utf16", errors) == "hellö"
            assert len(mod.f(ascii_codepoints, "ascii", errors)) == 127
            assert len(mod.f(ascii_codepoints, "utf8", errors)) == 127

        # None will be translated to NULL and then defaults to UTF-8 encoding
        for encoding in (None, "utf8"):
            assert mod.f(utf8_bytes, encoding, None) == "hellö"

            with pytest.raises(UnicodeDecodeError):
                mod.f(utf16_bytes, encoding, None)

            assert mod.f(utf16_bytes, encoding, "replace") == '��h\x00e\x00l\x00l\x00�\x00'
            assert mod.f(utf16_bytes, encoding, "ignore") == 'h\x00e\x00l\x00l\x00\x00'

        # test unknown encoding
        with pytest.raises(LookupError):
            mod.f(b"hello", "qwertyasdf13", None)

        with pytest.raises(SystemError):
            mod.f(None, None, None)
        with pytest.raises(TypeError):
            mod.f("hello", None, None)
        with pytest.raises(TypeError):
            mod.f(123, None, None)

    def test_Substring(self):
        import pytest
        import string
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_VARARGS)
            static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy_ssize_t start, end;
                if (nargs != 3) {
                    HPyErr_SetString(ctx, ctx->h_TypeError, "expected exactly 3 arguments");
                    return HPy_NULL;
                }

                start = HPyLong_AsSsize_t(ctx, args[1]);
                if (start == -1 && HPyErr_Occurred(ctx))
                    return HPy_NULL;

                end = HPyLong_AsSsize_t(ctx, args[2]);
                if (end == -1 && HPyErr_Occurred(ctx))
                    return HPy_NULL;

                return HPyUnicode_Substring(ctx, args[0], start, end);
            }
            @EXPORT(f)
            @INIT
        """)
        # start == end
        assert mod.f("hello", 0, 0) == ""
        assert mod.f("hello", 4, 4) == ""
        assert mod.f("hello", 5, 0) == ""
        # start < end
        assert mod.f("hello", 0, 5) == "hello"
        assert mod.f("hello", 0, 100) == "hello"
        assert mod.f('hello', 0, 1) == 'h'
        assert mod.f("hello", 0, 2) == "he"
        assert mod.f("hello", 2, 5) == "llo"
        assert mod.f("hello", 2, 4) == "ll"
        assert mod.f("hello", 100, 105) == ""
        # start > end
        assert mod.f("hello", 2000, 1000) == ""
        assert mod.f("hello", 2, 1) == ""

        with pytest.raises(IndexError):
            mod.f("hello", -2, 5)
        with pytest.raises(IndexError):
            mod.f("hello", 2, -1)

        # The following block is a variation of CPython's
        # 'string_tests.py: test_extended_getslice'. This compares substrings
        # with list slicing.
        s = string.ascii_letters + string.digits
        n = len(s)
        indices = (0, 1, 3, 41, 1000, n-1, n-2, n-37)
        for start in indices:
            for stop in indices:
                L = list(s)[start:stop]
                assert mod.f(s, start, stop) == "".join(L)
