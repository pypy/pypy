from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


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

    def test_slice_object(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3,4])
        assert arr[slice(1,3)].tolist() == [2,3]
        arr[slice(1,3)] = module.array('i', [21, 22, 23])
        assert arr.tolist() == [1, 21, 22, 23, 4]
        del arr[slice(1, 3)]
        assert arr.tolist() == [1, 23, 4]

    def test_buffer(self):
        import sys
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3,4])
        buf = buffer(arr)
        exc = raises(TypeError, "buf[1] = '1'")
        assert str(exc.value) == "buffer is read-only"
        if sys.byteorder == 'big':
            assert str(buf) == ('\0\0\0\x01'
                                '\0\0\0\x02'
                                '\0\0\0\x03'
                                '\0\0\0\x04')
        else:
            assert str(buf) == ('\x01\0\0\0'
                                '\x02\0\0\0'
                                '\x03\0\0\0'
                                '\x04\0\0\0')

    def test_pickle(self):
        import pickle
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3,4])
        s = pickle.dumps(arr)
        # pypy exports __dict__ on cpyext objects, so the pickle picks up the {} state value
        #assert s == "carray\n_reconstruct\np0\n(S'i'\np1\n(lp2\nI1\naI2\naI3\naI4\natp3\nRp4\n."
        rra = pickle.loads(s) # rra is arr backwards
        #assert arr.tolist() == rra.tolist()

    def test_binop_mul_impl(self):
        # check that rmul is called
        module = self.import_module(name='array')
        arr = module.array('i', [2])
        res = [1, 2, 3] * arr
        assert res == [1, 2, 3, 1, 2, 3]
        module.switch_multiply()
        res = [1, 2, 3] * arr
        assert res == [2, 4, 6]

    def test_subclass(self):
        import struct
        module = self.import_module(name='array')
        class Sub(module.array):
            pass

        arr = Sub('i', [2])
        res = [1, 2, 3] * arr
        assert res == [1, 2, 3, 1, 2, 3]
        
        val = module.readbuffer_as_string(arr)
        assert val == struct.pack('i', 2)

    def test_unicode_readbuffer(self):
        # Not really part of array, refactor
        import struct
        module = self.import_module(name='array')
        val = module.readbuffer_as_string(u'\u03a3')
        assert val.decode('utf32') == u'\u03a3'
