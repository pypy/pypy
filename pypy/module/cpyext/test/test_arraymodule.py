from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestArrayModule(AppTestCpythonExtensionBase):
    enable_leak_checking = False

    def test_basic(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3])
        assert arr.typecode == 'i'
        assert arr.itemsize == 4
        assert arr[2] == 3
        assert len(arr.buffer_info()) == 2
        arr.append(4)
        assert arr.tolist() == [1, 2, 3, 4]
        assert len(arr) == 4

    def test_iter(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3])
        sum = 0
        for i in arr: 
            sum += i
        assert sum == 6

    def test_index(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3,4])
        assert arr[3] == 4
        raises(IndexError, arr.__getitem__, 10)
        del arr[2]
        assert arr.tolist() == [1,2,4]
        arr[2] = 99
        assert arr.tolist() == [1,2,99]

    def test_slice_get(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3,4])
        assert arr[:].tolist() == [1,2,3,4]
        assert arr[1:].tolist() == [2,3,4]
        assert arr[:2].tolist() == [1,2]
        assert arr[1:3].tolist() == [2,3]

    def test_buffer(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3,4])
        # XXX big-endian
        assert str(buffer(arr)) == ('\x01\0\0\0'
                                    '\x02\0\0\0'
                                    '\x03\0\0\0'
                                    '\x04\0\0\0')

