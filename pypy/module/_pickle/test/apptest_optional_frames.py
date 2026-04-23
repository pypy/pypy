"""
Regression test for the buffer-lifetime crash triggered by test_oob_buffers
followed by test_optional_frames in the full test_pickle suite.

Ports DumpPickle_CLoadPickle.test_oob_buffers from
lib-python/3/test/pickletester.py.  Uses the pure-Python pickler for
dumps and the C unpickler for loads.

ZeroCopy* classes must be at module level so pickle can find them by name.
"""


class ZeroCopyBytes(bytes):
    readonly = True
    c_contiguous = True
    zero_copy_reconstruct = True

    def __reduce_ex__(self, protocol):
        import pickle
        if protocol >= 5:
            return type(self)._reconstruct, (pickle.PickleBuffer(self),), None
        else:
            return type(self)._reconstruct, (bytes(self),)

    @classmethod
    def _reconstruct(cls, obj):
        with memoryview(obj) as m:
            obj = m.obj
            if type(obj) is cls:
                return obj
            else:
                return cls(obj)


class ZeroCopyBytearray(bytearray):
    readonly = False
    c_contiguous = True
    zero_copy_reconstruct = True

    def __reduce_ex__(self, protocol):
        import pickle
        if protocol >= 5:
            return type(self)._reconstruct, (pickle.PickleBuffer(self),), None
        else:
            return type(self)._reconstruct, (bytes(self),)

    @classmethod
    def _reconstruct(cls, obj):
        with memoryview(obj) as m:
            obj = m.obj
            if type(obj) is cls:
                return obj
            else:
                return cls(obj)


def test_oob_buffers_py_dump_c_load():
    import sys, io, pickle, pickletools, _pickle
    mod = type(sys)('apptest_optional_frames')
    mod.ZeroCopyBytes = ZeroCopyBytes
    mod.ZeroCopyBytearray = ZeroCopyBytearray
    ZeroCopyBytes.__module__ = 'apptest_optional_frames'
    ZeroCopyBytearray.__module__ = 'apptest_optional_frames'
    sys.modules.setdefault('apptest_optional_frames', mod)

    def count_opcode(code, pickled):
        n = 0
        for op, _, _ in pickletools.genops(pickled):
            if op.code == code.decode('latin-1'):
                n += 1
        return n

    def dumps(obj, proto, buffer_callback=None):
        buf = io.BytesIO()
        pickle._Pickler(buf, proto, buffer_callback=buffer_callback).dump(obj)
        return buf.getvalue()

    def loads(data, buffers=None):
        return _pickle.loads(data, buffers=buffers)

    if pickle.HIGHEST_PROTOCOL < 5:
        return

    bytestring = b"abcdefgh"
    for obj in (ZeroCopyBytes(bytestring), ZeroCopyBytearray(bytestring)):
        for proto in range(5, pickle.HIGHEST_PROTOCOL + 1):
            buffers = []
            buffer_callback = lambda pb: buffers.append(pb.raw())
            data = dumps(obj, proto, buffer_callback=buffer_callback)
            assert b"abcdefgh" not in data
            assert count_opcode(pickle.SHORT_BINBYTES, data) == 0
            assert count_opcode(pickle.BYTEARRAY8, data) == 0
            assert count_opcode(pickle.NEXT_BUFFER, data) == 1
            assert count_opcode(pickle.READONLY_BUFFER, data) == (1 if obj.readonly else 0)

            if obj.c_contiguous:
                assert bytes(buffers[0]) == b"abcdefgh"

            new = loads(data, buffers=buffers)
            assert type(new) is type(obj)
            assert new == obj

            new = loads(data, buffers=iter(buffers))
            assert type(new) is type(obj)
            assert new == obj

    import gc
    gc.collect()


def test_optional_frames_py_dump_c_load():
    import io, pickle, pickletools, _pickle

    FRAME_SIZE_TARGET = 64 * 1024

    def dumps(obj, proto, **kwargs):
        buf = io.BytesIO()
        pickle._Pickler(buf, proto, **kwargs).dump(obj)
        return buf.getvalue()

    def loads(data):
        return _pickle.loads(data)

    def count_opcode(code, pickled):
        n = 0
        for op, _, _ in pickletools.genops(pickled):
            if op.name == code:
                n += 1
        return n

    def remove_frames(pickled, keep_frame=None):
        frame_starts = []
        frame_opcode_size = 9
        for opcode, _, pos in pickletools.genops(pickled):
            if opcode.name == 'FRAME':
                frame_starts.append(pos)
        newpickle = bytearray()
        last_frame_end = 0
        for i, pos in enumerate(frame_starts):
            if keep_frame and keep_frame(i):
                continue
            newpickle += pickled[last_frame_end:pos]
            last_frame_end = pos + frame_opcode_size
        newpickle += pickled[last_frame_end:]
        return newpickle

    if pickle.HIGHEST_PROTOCOL < 4:
        return

    frame_size = FRAME_SIZE_TARGET
    num_frames = 20
    for bytes_type in (bytes, bytearray):
        obj = {i: bytes_type([i]) * frame_size for i in range(num_frames)}
        for proto in range(4, pickle.HIGHEST_PROTOCOL + 1):
            pickled = dumps(obj, proto)

            frameless_pickle = remove_frames(pickled)
            assert count_opcode('FRAME', frameless_pickle) == 0
            assert obj == loads(frameless_pickle)

            some_frames_pickle = remove_frames(pickled, lambda i: i % 2)
            assert count_opcode('FRAME', some_frames_pickle) < count_opcode('FRAME', pickled)
            assert obj == loads(some_frames_pickle)
