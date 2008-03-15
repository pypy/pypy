# minimal tests.  See also lib-python/modified-2.4.1/test/test_array.

import autopath
import py
import struct
from pypy.conftest import gettestobjspace


class BaseArrayTests:
    # XXX very incomplete

    native_sizes = {'l': struct.calcsize('l')}

    def test_attributes(self):
        a = self.array.array('c')
        assert a.typecode == 'c'
        assert a.itemsize == 1
        a = self.array.array('l')
        assert a.typecode == 'l'
        assert a.itemsize == self.native_sizes['l']

    def test_imul(self):
        a = self.array.array('i', [12, 34])
        a *= 3
        assert a.tolist() == [12, 34] * 3

    def test_unicode(self):
        a = self.array.array('u')
        a.fromunicode(unichr(9999))
        assert len(a) == 1
        assert a.tolist() == [unichr(9999)]


class TestArrayOnTopOfCPython(BaseArrayTests):

    def setup_class(cls):
        if not hasattr(struct, 'pack_into'):
            py.test.skip("requires CPython >= 2.5")
        import new
        path = py.path.local(autopath.this_dir).dirpath().join('array.py')
        myarraymodule = new.module('array')
        execfile(str(path), myarraymodule.__dict__)
        cls.array = myarraymodule

    def test_unicode(self):
        py.test.skip("no 'u' type code in CPython's struct module")


class AppTestArray(BaseArrayTests):
    usemodules = ['struct']

    def setup_class(cls):
        """
        Create a space with the array module and import it for use by the
        tests.
        """
        cls.space = gettestobjspace(usemodules=cls.usemodules)
        cls.w_array = cls.space.appexec([], """():
            import array
            return array
        """)
        cls.w_native_sizes = cls.space.wrap(cls.native_sizes)


class AppTestArrayWithRawFFI(AppTestArray):
    """
    The same as the base class, but with a space that also includes the
    _rawffi module.  The array module internally uses it in this case.
    """
    usemodules = ['struct', '_rawffi']

    def test_buffer_info(self):
        a = self.array.array('l', [123, 456])
        assert a.itemsize == self.native_sizes['l']
        address, length = a.buffer_info()
        assert length == 2      # and not 2 * self.native_sizes['l']
        assert address != 0
        # should check the address via some unsafe peeking, but it's
        # not easy on top of py.py
