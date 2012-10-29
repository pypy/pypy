import py

from pypy.objspace.std.test import test_stringobject, test_unicodeobject

class TestRopeUnicodeObject(test_unicodeobject.TestUnicodeObject):
    spaceconfig = {"objspace.std.withropeunicode": True}


class AppTestRopeObject(test_stringobject.AppTestStringObject):
    spaceconfig = {"objspace.std.withropeunicode": True}

    def test_hash(self):
        # doesn't make sense, since ropes hash differently than cpython's
        # strings
        pass

    def test_replace_buffer(self):
        skip("XXX fix")

class AppTestRopeUnicode(object):
    spaceconfig = {"objspace.std.withropeunicode": True}

    def test_replace_buffer(self):
        skip("XXX fix")

class AppTestUnicodeRopeStdOnly(test_unicodeobject.AppTestUnicodeStringStdOnly):
    spaceconfig = {"objspace.std.withropeunicode": True}

class AppTestUnicodeRope(test_unicodeobject.AppTestUnicodeString):
    spaceconfig = dict(usemodules=('unicodedata',),
                       **{"objspace.std.withropeunicode": True})

    def test_replace_buffer(self):
        skip("XXX fix")

    def test_replace_with_buffer(self):
        skip("XXX fix")

    def test_rfind_corner_case(self):
        skip("XXX fix")

    def test_rsplit(self):
        skip("XXX fix")

