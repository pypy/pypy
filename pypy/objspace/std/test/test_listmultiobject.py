from pypy.interpreter.error import OperationError
from pypy.objspace.std.listmultiobject import W_ListMultiObject, \
    SliceTrackingListImplementation
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test import test_listobject
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace
from pypy.objspace.std.test.test_rangeobject import AppTestRangeListObject

class AppTest_ListMultiObject(test_listobject.AppTestW_ListObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultilist": True})

    def test_slice_with_step(self):
        l = range(20)
        l[0] = 14
        l2 = l[1:-1:2]
        assert l2 == range(1, 19, 2)

    def test_strlist_literal(self):
        import pypymagic
        l = ["1", "2", "3", "4", "5"]
        assert "StrListImplementation" in pypymagic.pypy_repr(l)

    def test_strlist_delitem(self):
        l = ["1", "2"]
        del l[0]
        assert l == ["2"]

    def test_strlist_append(self):
        import pypymagic
        l = []
        l.append("a")
        assert "StrListImplementation" in pypymagic.pypy_repr(l)
        l.extend(["b", "c", "d"])
        l += ["e", "f"]
        assert l == ["a", "b", "c", "d", "e", "f"]
        assert "StrListImplementation" in pypymagic.pypy_repr(l)

class AppTestRangeImplementation(AppTestRangeListObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultilist": True})
        cls.w_not_forced = cls.space.appexec([], """():
            import pypymagic
            def f(r):
                return (isinstance(r, list) and
                        "RangeImplementation" in pypymagic.pypy_repr(r))
            return f
        """)

    def test_sort(self):
        pass # won't work with multilists


class AppTest_FastSlice(test_listobject.AppTestW_ListObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withfastslice": True})

    def test_lazy_slice(self):
        import pypymagic
        l = [i for i in range(100)] # force it to not be a range impl
        l2 = l[1:-1]
        assert "SliceTrackingListImplementation" in pypymagic.pypy_repr(l)
        assert "SliceListImplementation" in pypymagic.pypy_repr(l2)
        result = 0
        for i in l2:
            result += i
        # didn't force l2
        assert "SliceListImplementation" in pypymagic.pypy_repr(l2)
        # force l2:
        l2.append(10)
        assert l2 == range(1, 99) + [10]

    def test_append_extend_dont_force(self):
        import pypymagic
        l = [i for i in range(100)] # force it to not be a range impl
        l2 = l[1:-1]
        assert "SliceTrackingListImplementation" in pypymagic.pypy_repr(l)
        assert "SliceListImplementation" in pypymagic.pypy_repr(l2)
        l.append(100)
        l.extend(range(101, 110))
        assert l == range(110)
        assert "SliceTrackingListImplementation" in pypymagic.pypy_repr(l)
        assert "SliceListImplementation" in pypymagic.pypy_repr(l2)

    def test_slice_of_slice(self):
        import pypymagic
        l = [i for i in range(100)] # force it to not be a range impl
        l2 = l[1:-1]
        l3 = l2[1:-1]
        l4 = l3[1:-1]
        assert l2 == range(1, 99)
        assert l3 == range(2, 98)
        assert l4 == range(3, 97)
        assert "SliceListImplementation" in pypymagic.pypy_repr(l4)
        l2[3] = 4
        assert "SliceListImplementation" not in pypymagic.pypy_repr(l2)
        assert "SliceListImplementation" in pypymagic.pypy_repr(l4)

    def test_delitem_to_empty(self):
        import pypymagic
        l = [i for i in range(100)] # force it to not be a range impl
        l1 = l[1:-1]
        del l1[:]
        assert "EmptyListImplementation" in pypymagic.pypy_repr(l1)

class TestSliceListImplementation(object):
    def setup_method(self,method):
        self.space = FakeSpace()

    def test_simple(self):
        impl = SliceTrackingListImplementation(self.space, range(20))
        impl2 = impl.getitem_slice(2, 14)
        assert impl2.getitem(2) == 4
        impl = impl.setitem(4, 10)
        assert impl.getitem(4) == 10
        # check that impl2 works after detaching
        assert impl2.getitem(2) == 4
        impl2 = impl2.setitem(2, 5)
        assert impl2.getitem(2) == 5

class AppTest_SmartListObject(test_listobject.AppTestW_ListObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{
            "objspace.std.withsmartresizablelist": True})


def _set_chunk_size_bits(bits):
    from pypy.conftest import option
    if not option.runappdirect:
        from pypy.objspace.std import listmultiobject
        old_value = listmultiobject.CHUNK_SIZE_BITS
        listmultiobject.CHUNK_SIZE_BITS = bits
        listmultiobject.CHUNK_SIZE = 2**bits
        return old_value
    return -1

class AppTest_ChunkListObject(test_listobject.AppTestW_ListObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withchunklist": True})
        cls.chunk_size_bits = _set_chunk_size_bits(2)

    def teardown_class(cls):
        _set_chunk_size_bits(cls.chunk_size_bits)

