from pypy.module._ffi.test.test_funcptr import BaseAppTestFFI

class AppTestStruct(BaseAppTestFFI):

    def setup_class(cls):
        BaseAppTestFFI.setup_class.im_func(cls)
        #
        def read_raw_mem(self, addr, typename, length):
            import ctypes
            addr = ctypes.cast(addr, ctypes.c_void_p)
            c_type = getattr(ctypes, typename)
            array_type = ctypes.POINTER(c_type * length)
            ptr_array = ctypes.cast(addr, array_type)
            array = ptr_array[0]
            lst = [array[i] for i in range(length)]
            return lst
        cls.w_read_raw_mem = cls.space.wrap(read_raw_mem)
        
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

    def test_getfield_setfield(self):
        from _ffi import _StructDescr, Field, types
        longsize = types.slong.sizeof()
        fields = [
            Field('x', types.slong),
            Field('y', types.slong),
            ]
        descr = _StructDescr('foo', fields)
        struct = descr.allocate()
        struct.setfield('x', 42)
        struct.setfield('y', 43)
        assert struct.getfield('x') == 42
        assert struct.getfield('y') == 43
        mem = self.read_raw_mem(struct.getaddr(), 'c_long', 2)
        assert mem == [42, 43]

    def test_missing_field(self):
        from _ffi import _StructDescr, Field, types
        longsize = types.slong.sizeof()
        fields = [
            Field('x', types.slong),
            Field('y', types.slong),
            ]
        descr = _StructDescr('foo', fields)
        struct = descr.allocate()
        raises(AttributeError, "struct.getfield('missing')")
        raises(AttributeError, "struct.setfield('missing', 42)")
