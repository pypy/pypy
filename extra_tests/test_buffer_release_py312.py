# Like test_buffer_release.py, for the stdlib code of Python 3.12: the
# asyncio socket transport keeps views of the data it sends, and on PyPy3.12
# an array.array cannot be resized while a view of it is alive either
# (issue 5612).
import array
import asyncio
import base64
import bz2
import gc
import lzma
import os
import socket
import sqlite3
import warnings

import pytest


def _transport_send(write):
    async def main():
        loop = asyncio.get_running_loop()
        a, b = socket.socketpair()
        with b:
            transport, _ = await loop.create_connection(asyncio.Protocol,
                                                        sock=a)
            write(transport)
            transport.close()
            await asyncio.sleep(0)
            received = b""
            while len(received) < 6:
                received += b.recv(100)
            return received
    return asyncio.run(main())


def test_transport_write_bytearray_then_resize():
    data = bytearray(b"abcdef")

    def write(transport):
        transport.write(data)
        del data[3:]

    assert _transport_send(write) == b"abcdef"


def test_transport_writelines_bytearray_then_resize():
    data = [bytearray(b"abc"), bytearray(b"def")]

    def write(transport):
        transport.writelines(data)
        for item in data:
            item.clear()

    assert _transport_send(write) == b"abcdef"


def test_transport_buffered_bytearray_then_resize():
    # data that waits in the transport's buffer, behind data that the
    # socket could not take, must be released once it has been sent; and
    # the caller's own memoryview must not be released.  gc.disable() keeps
    # the GC from releasing the views first.
    fill = b"x" * (4 * 1024 * 1024)
    view = memoryview(b"abc")
    data = [bytearray(b"d"), bytearray(b"e")]

    async def main():
        loop = asyncio.get_running_loop()
        a, b = socket.socketpair()
        b.setblocking(False)
        with b:
            transport, _ = await loop.create_connection(asyncio.Protocol,
                                                        sock=a)
            transport.write(fill)
            assert transport.get_write_buffer_size() > 0
            transport.write(view)
            transport.writelines(data)
            received = b""
            while len(received) < len(fill) + 5:
                try:
                    received += b.recv(1 << 16)
                except BlockingIOError:
                    await asyncio.sleep(0.001)
            transport.close()
            return received[-5:]

    gc.disable()
    try:
        assert asyncio.run(main()) == b"abcde"
        assert view.tobytes() == b"abc"
        for item in data:
            item.clear()
    finally:
        gc.enable()


def test_blob_slice_assignment_bytearray_then_resize():
    con = sqlite3.connect(":memory:")
    con.execute("create table t(b blob)")
    con.execute("insert into t values (zeroblob(6))")
    data = bytearray(b"abcdef")
    with con.blobopen("t", "b", 1) as blob:
        blob[0:6] = data
        del data[3:]
        assert blob.read() == b"abcdef"
    con.close()


@pytest.mark.parametrize("mod", [bz2, lzma])
def test_compressed_file_write_array_then_resize(tmp_path, mod):
    data = array.array("B", b"abcdef")
    path = os.path.join(tmp_path, "f")
    with mod.open(path, "wb") as f:
        f.write(data)
        data.append(0)
    with mod.open(path, "rb") as f:
        assert f.read() == b"abcdef"


@pytest.mark.parametrize("modname", ["wave", "aifc", "sunau"])
def test_writeframes_array_then_resize(tmp_path, modname):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        mod = pytest.importorskip(modname)
    data = array.array("h", [1, 2, 3, 4])
    path = os.path.join(tmp_path, "f")
    with mod.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(data)
        data.append(5)
    with mod.open(path, "rb") as f:
        assert f.getnframes() == 4


def test_base64_array_then_resize():
    data = array.array("B", b"YWJjZGVm")
    assert base64.b64decode(data) == b"abcdef"
    data.append(0)
    for encode, decode in [(base64.b32encode, base64.b32decode),
                           (base64.a85encode, base64.a85decode),
                           (base64.b85encode, base64.b85decode)]:
        data = array.array("B", b"abcdef")
        assert decode(encode(data)) == b"abcdef"
        data.append(0)
