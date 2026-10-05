# The stdlib must release the views it takes of a caller's buffer before it
# returns.  PyPy only releases a view that is still alive when the GC
# collects it, and a bytearray cannot be resized while a view of it is
# alive, so after such a call 'del data[...]' raised BufferError
# (issue 5612).
import array
import asyncio
import base64
import bz2
import ctypes
import gc
import hashlib
import hmac
import io
import lzma
import multiprocessing
import os
import pathlib
import socket
import sqlite3
import ssl
import subprocess
import sys
import urllib.parse
import warnings

import pytest

CERTDIR = os.path.join(os.path.dirname(__file__), '..', 'lib-python', '3',
                       'test', 'certdata')


def test_pathlib_write_bytes_bytearray_then_resize(tmp_path):
    data = bytearray(b"abcdef")
    path = pathlib.Path(tmp_path, "f")
    assert path.write_bytes(data) == 6
    del data[3:]
    assert path.read_bytes() == b"abcdef"


def test_parse_qs_bytearray_then_resize():
    data = bytearray(b"a=1&b=2")
    assert urllib.parse.parse_qs(data) == {b"a": [b"1"], b"b": [b"2"]}
    del data[3:]
    assert urllib.parse.parse_qsl(data) == [(b"a", b"1")]
    del data[1:]


def test_lzma_bytearray_then_resize(tmp_path):
    data = bytearray(b"abcdef")
    compressed = bytearray(lzma.compress(data))
    del data[3:]
    assert lzma.decompress(compressed) == b"abcdef"
    del compressed[3:]

    data = bytearray(b"abcdef")
    path = os.path.join(tmp_path, "f.xz")
    with lzma.open(path, "wb") as f:
        f.write(data)
        del data[3:]
    with lzma.open(path, "rb") as f:
        assert f.read() == b"abcdef"


def test_base64_encodebytes_bytearray_then_resize():
    data = bytearray(b"abcdef")
    encoded = bytearray(base64.encodebytes(data))
    del data[3:]
    assert base64.decodebytes(encoded) == b"abcdef"
    del encoded[3:]


def test_file_digest_bytesio_then_write():
    expected = hashlib.sha256(b"abcdef").hexdigest()
    f = io.BytesIO(b"abcdef")
    assert hashlib.file_digest(f, "sha256").hexdigest() == expected
    f.write(b"more")


def test_compare_digest_bytearray_then_resize():
    a = bytearray(b"abcdef")
    b = bytearray(b"abcdef")
    assert hmac.compare_digest(a, b)
    del a[3:]
    del b[3:]


class FakeSocket:
    def __init__(self, response=b""):
        self.response = response
        self.sent = bytearray()

    def sendall(self, data):
        self.sent += data

    def makefile(self, mode, bufsize=None):
        return io.BytesIO(self.response)

    def close(self):
        pass


def test_http_request_body_bytearray_then_resize():
    import http.client
    body = bytearray(b"abcdef")
    conn = http.client.HTTPConnection("example.com")
    conn.sock = FakeSocket()
    conn.request("POST", "/", body=body)
    del body[3:]
    assert conn.sock.sent.endswith(b"\r\nContent-Length: 6\r\n\r\nabcdef")


@pytest.mark.parametrize("headers, payload", [
    (b"Content-Length: 6", b"abcdef"),
    (b"Transfer-Encoding: chunked", b"6\r\nabcdef\r\n0\r\n\r\n"),
])
def test_http_response_readinto_bytearray_then_resize(headers, payload):
    import http.client
    sock = FakeSocket(b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n\r\n" + payload)
    response = http.client.HTTPResponse(sock)
    response.begin()
    buf = bytearray(10)
    assert response.readinto(buf) == 6
    del buf[6:]
    assert buf == b"abcdef"


def test_subprocess_input_bytearray_then_resize():
    data = bytearray(b"abcdef")
    cmd = [sys.executable, "-c",
           "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"]
    result = subprocess.run(cmd, input=data, capture_output=True, check=True)
    del data[3:]
    assert result.stdout == b"abcdef"


def test_connection_send_bytes_bytearray_then_resize():
    reader, writer = multiprocessing.Pipe(duplex=False)
    try:
        data = bytearray(b"abcdef")
        writer.send_bytes(data)
        del data[3:]
        assert reader.recv_bytes() == b"abcdef"
    finally:
        reader.close()
        writer.close()


def test_ctypes_from_buffer_copy_bytearray_then_resize():
    data = bytearray(b"abcdef")
    copy = (ctypes.c_char * 6).from_buffer_copy(data)
    del data[3:]
    assert copy.raw == b"abcdef"


def test_ssl_password_bytearray_then_resize():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    password = bytearray(b"somepass")
    ctx.load_cert_chain(os.path.join(CERTDIR, "keycert.passwd.pem"),
                        password=password)
    password.clear()


def test_ssl_cadata_bytearray_then_resize():
    with open(os.path.join(CERTDIR, "pycacert.pem")) as f:
        pem = f.read()
    pem = pem[pem.index("-----BEGIN CERTIFICATE-----"):]
    cadata = bytearray(ssl.PEM_cert_to_DER_cert(pem))
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(cadata=cadata)
    cadata.clear()
    assert ctx.cert_store_stats()["x509_ca"] == 1


def test_audioop_bytearray_then_resize():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        audioop = pytest.importorskip("audioop")
    frames = b"\x01\x00\x05\x00\x02\x00\x07\x00"
    data = bytearray(frames)
    for func, args in [(audioop.getsample, (2, 1)), (audioop.max, (2,)),
                       (audioop.rms, (2,)), (audioop.avgpp, (2,)),
                       (audioop.lin2lin, (2, 1)), (audioop.reverse, (2,)),
                       (audioop.findfit, (frames[:4],))]:
        assert func(data, *args) == func(frames, *args)
    del data[4:]


def test_sock_sendall_bytearray_then_resize():
    # big enough for the first send() to be partial
    data = bytearray(b"x" * (8 * 1024 * 1024))

    async def main():
        loop = asyncio.get_running_loop()
        a, b = socket.socketpair()
        with a, b:
            a.setblocking(False)
            b.setblocking(False)
            received = 0

            async def read_all():
                nonlocal received
                while received < len(data):
                    received += len(await loop.sock_recv(b, 1 << 20))

            reader = asyncio.ensure_future(read_all())
            await loop.sock_sendall(a, data)
            await reader
            return received

    assert asyncio.run(main()) == len(data)
    del data[3:]


@pytest.mark.skipif(sys.platform == "win32", reason="unix pipe transport")
def test_pipe_transport_write_bytearray_then_resize():
    data = bytearray(b"abcdef")

    async def main():
        loop = asyncio.get_running_loop()
        r, w = os.pipe()
        with open(r, "rb") as rfile, open(w, "wb", buffering=0) as wfile:
            transport, _ = await loop.connect_write_pipe(
                asyncio.BaseProtocol, wfile)
            transport.write(data)
            transport.close()
            del data[3:]
            await asyncio.sleep(0)
            return rfile.read()

    assert asyncio.run(main()) == b"abcdef"


# Python 3.12's asyncio socket transport keeps views of the data it sends,
# and on PyPy3.12 an array.array cannot be resized while a view of it is
# alive either.


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
