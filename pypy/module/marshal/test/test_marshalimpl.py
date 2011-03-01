from pypy.module.marshal import interp_marshal
from pypy.interpreter.error import OperationError
from pypy.conftest import gettestobjspace
import sys


class AppTestMarshalMore:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('array',))
        cls.space = space

    def test_long_0(self):
        import marshal
        z = 0L
        z1 = marshal.loads(marshal.dumps(z))
        assert z == z1
        assert type(z1) is long

    def test_unmarshal_int64(self):
        # test that we can unmarshal 64-bit ints on 32-bit platforms
        # (of course we only test that if we're running on such a
        # platform :-)
        import marshal
        z = marshal.loads('I\x00\xe4\x0bT\x02\x00\x00\x00')
        assert z == 10000000000
        z = marshal.loads('I\x00\x1c\xf4\xab\xfd\xff\xff\xff')
        assert z == -10000000000
        z = marshal.loads('I\x88\x87\x86\x85\x84\x83\x82\x01')
        assert z == 108793946209421192
        z = marshal.loads('I\xd8\xd8\xd9\xda\xdb\xdc\xcd\xfe')
        assert z == -0x0132232425262728

    def test_buffer(self):
        import marshal
        z = marshal.loads(buffer('i\x02\x00\x00\x00???'))
        assert z == 2

    def test_marshal_buffer_object(self):
        import marshal
        s = marshal.dumps(buffer('foobar'))
        t = marshal.loads(s)
        assert type(t) is str and t == 'foobar'

    def test_marshal_bufferlike_object(self):
        import marshal, array
        s = marshal.dumps(array.array('c', 'asd'))
        t = marshal.loads(s)
        assert type(t) is str and t == 'asd'

    def test_unmarshal_evil_long(self):
        import marshal
        raises(ValueError, marshal.loads, 'l\x02\x00\x00\x00\x00\x00\x00\x00')
        z = marshal.loads('I\x00\xe4\x0bT\x02\x00\x00\x00')
        assert z == 10000000000
        z = marshal.loads('I\x00\x1c\xf4\xab\xfd\xff\xff\xff')
        assert z == -10000000000


class AppTestMarshalSmallLong(AppTestMarshalMore):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('array',),
                                **{"objspace.std.withsmalllong": True})
        cls.space = space
