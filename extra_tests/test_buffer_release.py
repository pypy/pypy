# The stdlib must release the views it takes of a caller's buffer before it
# returns.  PyPy only releases a view that is still alive when the GC
# collects it, and a bytearray cannot be resized while a view of it is
# alive, so after such a call 'del data[...]' raised BufferError
# (issue 5612).
import asyncio
import base64
import ctypes
import hashlib
import hmac
import io
import lzma
import multiprocessing
import os
import pathlib
import socket
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
