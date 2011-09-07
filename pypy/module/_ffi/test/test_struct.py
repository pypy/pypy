from pypy.module._ffi.test.test_funcptr import BaseAppTestFFI

class AppTestStruct(BaseAppTestFFI):

    def test__StructDescr(self):
        from _ffi import _StructDescr, Field, types
        longsize = types.slong.sizeof()
        fields = [
            Field('x', types.slong),
            Field('y', types.slong),
            ]
        descr = _StructDescr('foo', fields)
        assert descr.ffitype.sizeof() == longsize*2
        assert descr.ffitype.name == 'struct foo'

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
        assert Point._struct_.ffitype.sizeof() == longsize*2
        assert Point._struct_.ffitype.name == 'struct Point'
