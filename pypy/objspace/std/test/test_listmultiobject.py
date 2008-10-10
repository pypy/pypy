from pypy.interpreter.error import OperationError
from pypy.objspace.std.listmultiobject import W_ListMultiObject, \
    SliceTrackingListImplementation
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test import test_listobject
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace
from pypy.objspace.std.test import test_rangeobject

class BaseAppTest_ListMultiObject(test_listobject.AppTestW_ListObject):
    @staticmethod
    def setup_class(cls, conf_switch='withmultilist', impl_tag=''):
        cls.space = gettestobjspace(**{"objspace.std."+conf_switch: True})
        cls.w_impl_used = cls.space.appexec([cls.space.wrap(impl_tag)],
                                            """(impl_tag):
            import __pypy__
            def impl_used(obj, tag=''):
                if not tag:
                    if impl_tag:
                        tag=impl_tag
                    else:
                        skip('test not enabled (impl_tag not set)')
                return tag in __pypy__.internal_repr(obj)
            return impl_used
        """)
        
    def test_implementation_is_used(self):
        l = ["1", "2", "3", "4", "5"]
        assert self.impl_used(l)
        l = list(["1", "2", "3", "4", "5"])
        assert self.impl_used(l)
        l=[]
        l.append('a')
        assert self.impl_used(l)
        l = ["6", "8", "3", "1", "5"]
        l.sort()
        assert self.impl_used(l)
        assert self.impl_used([0])
        assert self.impl_used(list([0]))
        # These few here ^ would have failed before, but for good coverage,
        # all the list methods etc. should be tested also...

class AppTest_ListMultiObject(BaseAppTest_ListMultiObject):
    def setup_class(cls):
        BaseAppTest_ListMultiObject.setup_class(cls)

    def test_slice_with_step(self):
        l = range(20)
        l[0] = 14
        l2 = l[1:-1:2]
        assert l2 == range(1, 19, 2)

    def test_strlist_literal(self):
        l = ["1", "2", "3", "4", "5"]
        assert self.impl_used(l, "StrListImplementation")

    def test_strlist_delitem(self):
        l = ["1", "2"]
        del l[0]
        assert l == ["2"]

    def test_strlist_append(self):
        l = []
        l.append("a")
        assert self.impl_used(l, "StrListImplementation")
        l.extend(["b", "c", "d"])
        l += ["e", "f"]
        assert l == ["a", "b", "c", "d", "e", "f"]
        assert self.impl_used(l, "StrListImplementation")

class AppTestRangeImplementation(test_rangeobject.AppTestRangeListObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultilist": True})
        cls.w_not_forced = cls.space.appexec([], """():
            import __pypy__
            def f(r):
                return (isinstance(r, list) and
                        "RangeImplementation" in __pypy__.internal_repr(r))
            return f
        """)
        cls.w_SORT_FORCES_LISTS = cls.space.wrap(True)


class AppTest_FastSlice(BaseAppTest_ListMultiObject):
    def setup_class(cls):
        BaseAppTest_ListMultiObject.setup_class(cls, 'withfastslice')

    def test_lazy_slice(self):
        l = [i for i in range(100)] # force it to not be a range impl
        l2 = l[1:-1]
        assert self.impl_used(l, "SliceTrackingListImplementation")
        assert self.impl_used(l2, "SliceListImplementation")
        result = 0
        for i in l2:
            result += i
        # didn't force l2
        assert self.impl_used(l2, "SliceListImplementation")
        # force l2:
        l2.append(10)
        assert l2 == range(1, 99) + [10]

    def test_append_extend_dont_force(self):
        l = [i for i in range(100)] # force it to not be a range impl
        l2 = l[1:-1]
        assert self.impl_used(l, "SliceTrackingListImplementation")
        assert self.impl_used(l2, "SliceListImplementation")
        l.append(100)
        l.extend(range(101, 110))
        assert l == range(110)
        assert self.impl_used(l, "SliceTrackingListImplementation")
        assert self.impl_used(l2, "SliceListImplementation")

    def test_slice_of_slice(self):
        l = [i for i in range(100)] # force it to not be a range impl
        l2 = l[1:-1]
        l3 = l2[1:-1]
        l4 = l3[1:-1]
        assert l2 == range(1, 99)
        assert l3 == range(2, 98)
        assert l4 == range(3, 97)
        assert self.impl_used(l4, "SliceListImplementation")
        l2[3] = 4
        assert not self.impl_used(l2, "SliceListImplementation")
        assert self.impl_used(l4, "SliceListImplementation")

    def test_delitem_to_empty(self):
        import __pypy__
        l = [i for i in range(100)] # force it to not be a range impl
        l1 = l[1:-1]
        del l1[:]
        assert self.impl_used(l1, "EmptyListImplementation")

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

class AppTest_SmartListObject(BaseAppTest_ListMultiObject):
    def setup_class(cls):
        BaseAppTest_ListMultiObject.setup_class(cls, 'withsmartresizablelist',
                                                 'SmartResizableList')


def _set_chunk_size_bits(bits):
    from pypy.conftest import option
    if not option.runappdirect:
        from pypy.objspace.std import listmultiobject
        old_value = listmultiobject.CHUNK_SIZE_BITS
        listmultiobject.CHUNK_SIZE_BITS = bits
        listmultiobject.CHUNK_SIZE = 2**bits
        return old_value
    return -1

class AppTest_ChunkListObject(BaseAppTest_ListMultiObject):

    def setup_class(cls):
        BaseAppTest_ListMultiObject.setup_class(cls, 'withchunklist',
                                                 'ChunkedList')
        cls.chunk_size_bits = _set_chunk_size_bits(2)

    def teardown_class(cls):
        _set_chunk_size_bits(cls.chunk_size_bits)

