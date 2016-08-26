import py
import struct
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from rpython.rlib.buffer import Buffer

class AppTestMemoryView:
    spaceconfig = dict(usemodules=['array'])

    def test_basic(self):
        v = memoryview(b"abc")
        assert v.tobytes() == b"abc"
        assert len(v) == 3
        assert v[0] == ord('a')
        assert list(v) == [97, 98, 99]
        assert v.tolist() == [97, 98, 99]
        assert v[1] == ord("b")
        assert v[-1] == ord("c")
        exc = raises(TypeError, "v[1] = b'x'")
        assert str(exc.value) == "cannot modify read-only memory"
        assert v.readonly is True
        w = v[1:234]
        assert isinstance(w, memoryview)
        assert len(w) == 2
        exc = raises(NotImplementedError, "v[0:2:2]")
        assert str(exc.value) == ""
        exc = raises(TypeError, "memoryview('foobar')")

    def test_rw(self):
        data = bytearray(b'abcefg')
        v = memoryview(data)
        assert v.readonly is False
        v[0] = ord('z')
        assert data == bytearray(eval("b'zbcefg'"))
        v[1:4] = b'123'
        assert data == bytearray(eval("b'z123fg'"))
        v[0:3] = v[2:5]
        assert data == bytearray(eval("b'23f3fg'"))
        exc = raises(ValueError, "v[2:3] = b'spam'")
        assert str(exc.value) == "cannot modify size of memoryview object"
        exc = raises(NotImplementedError, "v[0:2:2] = b'spam'")
        assert str(exc.value) == ""

    def test_memoryview_attrs(self):
        v = memoryview(b"a"*100)
        assert v.format == "B"
        assert v.itemsize == 1
        assert v.shape == (100,)
        assert v.ndim == 1
        assert v.strides == (1,)

    def test_suboffsets(self):
        v = memoryview(b"a"*100)
        assert v.suboffsets == ()

    def test_compare(self):
        assert memoryview(b"abc") == b"abc"
        assert memoryview(b"abc") == bytearray(b"abc")
        assert memoryview(b"abc") != 3
        assert memoryview(b'ab') == b'ab'
        assert b'ab' == memoryview(b'ab')
        assert not (memoryview(b'ab') != b'ab')
        assert memoryview(b'ab') == memoryview(b'ab')
        assert not (memoryview(b'ab') != memoryview(b'ab'))
        assert memoryview(b'ab') != memoryview(b'abc')
        raises(TypeError, "memoryview(b'ab') <  memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') <= memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') >  memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') >= memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') <  memoryview(b'abc')")
        raises(TypeError, "memoryview(b'ab') <= memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') >  memoryview(b'aa')")
        raises(TypeError, "memoryview(b'ab') >= memoryview(b'ab')")

    def test_array_buffer(self):
        import array
        b = memoryview(array.array("B", [1, 2, 3]))
        assert len(b) == 3
        assert b[0:3] == b"\x01\x02\x03"

    def test_nonzero(self):
        assert memoryview(b'\x00')
        assert not memoryview(b'')
        import array
        assert memoryview(array.array("B", [0]))
        assert not memoryview(array.array("B", []))

    def test_bytes(self):
        assert bytes(memoryview(b'hello')) == b'hello'

    def test_repr(self):
        assert repr(memoryview(b'hello')).startswith('<memory at 0x')

    def test_hash(self):
        assert hash(memoryview(b'hello')) == hash(b'hello')

    def test_weakref(self):
        import weakref
        m = memoryview(b'hello')
        weakref.ref(m)

    def test_getitem_only_ints(self):
        class MyInt(object):
          def __init__(self, x):
            self.x = x

          def __int__(self):
            return self.x

        buf = memoryview(b'hello world')
        raises(TypeError, "buf[MyInt(0)]")
        raises(TypeError, "buf[MyInt(0):MyInt(5)]")

    def test_release(self):
        v = memoryview(b"a"*100)
        v.release()
        raises(ValueError, len, v)
        raises(ValueError, v.tolist)
        raises(ValueError, v.tobytes)
        raises(ValueError, "v[0]")
        raises(ValueError, "v[0] = b'a'")
        raises(ValueError, "v.format")
        raises(ValueError, "v.itemsize")
        raises(ValueError, "v.ndim")
        raises(ValueError, "v.readonly")
        raises(ValueError, "v.shape")
        raises(ValueError, "v.strides")
        raises(ValueError, "v.suboffsets")
        raises(ValueError, "with v as cm: pass")
        raises(ValueError, "memoryview(v)")
        assert v == v
        assert v != memoryview(b"a"*100)
        assert v != b"a"*100
        assert "released memory" in repr(v)

    def test_context_manager(self):
        v = memoryview(b"a"*100)
        with v as cm:
            assert cm is v
        raises(ValueError, bytes, v)
        assert "released memory" in repr(v)

    def test_int_array_buffer(self):
        import array
        m = memoryview(array.array('i', list(range(10))))
        assert m.format == 'i'
        assert m.itemsize == 4
        assert len(m) == 10
        assert len(m.tobytes()) == 40
        assert m[0] == 0
        m[0] = 1
        assert m[0] == 1

    def test_int_array_slice(self):
        import array
        m = memoryview(array.array('i', list(range(10))))
        slice = m[2:8]
        assert slice.format == 'i'
        assert slice.itemsize == 4
        assert len(slice) == 6
        assert len(slice.tobytes()) == 24
        assert slice[0] == 2
        slice[0] = 1
        assert slice[0] == 1
        assert m[2] == 1

    def test_pypy_raw_address_base(self):
        raises(ValueError, memoryview(b"foobar")._pypy_raw_address)
        a = memoryview(bytearray(b"foobar"))._pypy_raw_address()
        assert a != 0

    def test_hex(self):
        assert memoryview(b"abc").hex() == u'616263'

class MockBuffer(Buffer):
    def __init__(self, space, w_arr, w_dim, w_fmt, \
                 w_itemsize, w_strides, w_shape):
        self.space = space
        self.w_arr = w_arr
        self.arr = []
        self.ndim = space.int_w(w_dim)
        self.fmt = space.str_w(w_fmt)
        self.itemsize = space.int_w(w_itemsize)
        self.strides = []
        for w_i in w_strides.getitems_unroll():
            self.strides.append(space.int_w(w_i))
        self.shape = []
        for w_i in w_shape.getitems_unroll():
            self.shape.append(space.int_w(w_i))
        self.readonly = True
        self.shape.append(space.len_w(w_arr))
        self.data = []
        itemsize = 1
        worklist = [(1,w_arr)]
        while worklist:
            dim, w_work = worklist.pop()
            if space.isinstance_w(w_work, space.w_list):
                for j, w_obj in enumerate(w_work.getitems_unroll()):
                    worklist.insert(0, (dim+1, w_obj))
                continue
            self.data.append(space.int_w(w_work))

    def getslice(self, start, stop, step, size):
        items = []
        bytecount = (stop - start)
        # data is stores as list of ints, thus this gets around the
        # issue that one cannot advance in bytes
        count = bytecount // size
        start = start // size
        for i in range(start, start+count, step):
            items.append(self.getitem(i))
        return ''.join(items)

    def getformat(self):
        return self.fmt

    def getitem(self, index):
        return struct.pack(self.fmt, self.data[index])

    def getlength(self):
        return len(self.data) * self.itemsize

    def getitemsize(self):
        return self.itemsize

    def getndim(self):
        return self.ndim

    def getstrides(self):
        return self.strides

    def getshape(self):
        return self.shape

class W_MockArray(W_Root):
    def __init__(self, w_list, w_dim, w_fmt, w_size, w_strides, w_shape):
        self.w_list = w_list
        self.w_dim = w_dim
        self.w_fmt = w_fmt
        self.w_size = w_size
        self.w_strides = w_strides
        self.w_shape = w_shape

    @staticmethod
    def descr_new(space, w_type, w_list, w_dim, w_fmt, \
                         w_size, w_strides, w_shape):
        return W_MockArray(w_list, w_dim, w_fmt, w_size, w_strides, w_shape)

    def buffer_w(self, space, flags):
        return MockBuffer(space, self.w_list, self.w_dim, self.w_fmt, \
                          self.w_size, self.w_strides, self.w_shape)

W_MockArray.typedef = TypeDef("MockArray",
    __new__ = interp2app(W_MockArray.descr_new),
)

from pypy.objspace.std.transparent import register_proxyable
from pypy.conftest import option

class AppTestMemoryViewMicroNumPyPy(object):
    spaceconfig = dict(usemodules=[])
    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("Impossible to run on appdirect")
        cls.w_MockArray = cls.space.gettypefor(W_MockArray)

    def test_tuple_indexing(self):
        content = self.MockArray([[0,1,2,3], [4,5,6,7], [8,9,10,11]],
                                 dim=2, fmt='B', size=1,
                                 strides=[4,1], shape=[3,4])
        view = memoryview(content)
        assert view[0,0] == 0
        assert view[2,0] == 8
        assert view[2,3] == 11
        assert view[-1,-1] == 11
        assert view[-3,-4] == 0

        try:
            view.__getitem__((2**63-1,0))
            assert False, "must not succeed"
        except IndexError: pass

        try:
            view.__getitem__((0, 0, 0))
            assert False, "must not succeed"
        except TypeError: pass

    def test_tuple_indexing_int(self):
        content = self.MockArray([ [[1],[2],[3]], [[4],[5],[6]] ],
                                 dim=3, fmt='i', size=4,
                                 strides=[12,4,4], shape=[2,3,1])
        view = memoryview(content)
        assert view[0,0,0] == 1
        assert view[-1,2,0] == 6

