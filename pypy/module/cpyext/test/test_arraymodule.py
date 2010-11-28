from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestArrayModule(AppTestCpythonExtensionBase):
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
        self.cleanup_references()

    def test_iter(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3])
        sum = 0
        for i in arr: 
            sum += i
        assert sum == 6
        self.cleanup_references()

    def test_index(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3,4])
        assert arr[3] == 4
        raises(IndexError, arr.__getitem__, 10)
        del arr[2]
        assert arr.tolist() == [1,2,4]
        arr[2] = 99
        assert arr.tolist() == [1,2,99]
        self.cleanup_references()

    def test_slice_get(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3,4])
        assert arr[:].tolist() == [1,2,3,4]
        assert arr[1:].tolist() == [2,3,4]
        assert arr[:2].tolist() == [1,2]
        assert arr[1:3].tolist() == [2,3]
        self.cleanup_references()
