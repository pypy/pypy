from pypy.module._ffi.test.test_funcptr import BaseAppTestFFI

class AppTestStruct(BaseAppTestFFI):

    def test__StructDescr(self):
        from _ffi import _StructDescr, types
        longsize = types.slong.sizeof()
        descr = _StructDescr('foo', longsize*2, 0, [types.slong, types.slong])
        assert descr.name == 'foo'
        assert descr.ffitype.sizeof() == longsize*2
        assert repr(descr.ffitype) == '<ffi type struct foo>'

    def test_compute_shape(self):
        from _ffi import Structure, Field, types
        class Point(Structure):
            _fields_ = [
                Field('x', types.slong),
                Field('y', types.slong),
                ]

        longsize = types.slong.sizeof()
        assert isinstance(Point.x, Field)
        assert isinstance(Point.y, Field)
        assert Point.x.offset == 0
        assert Point.y.offset == longsize
        assert Point._struct_.name == 'Point'
        assert Point._struct_.ffitype.sizeof() == longsize*2
