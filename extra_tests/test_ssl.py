import pytest
import _ssl
import ssl
import os
import hashlib

CERTDIR = os.path.join(os.path.dirname(__file__), '..', 'lib-python', '3',
                       'test', 'certdata')


@pytest.mark.skipif(os.name != 'posix', reason="needs /dev/null")
def test_invalid_file():
    # gh-5120: do not segfault
    with pytest.raises(_ssl.SSLError):
        cert = _ssl._test_decode_cert("/dev/null")


def _bio_pair():
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(os.path.join(CERTDIR, 'keycert.pem'))
    client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client_ctx.check_hostname = False
    client_ctx.verify_mode = ssl.CERT_NONE
    c_in, c_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    s_in, s_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    client = client_ctx.wrap_bio(c_in, c_out, server_hostname="localhost")
    server = server_ctx.wrap_bio(s_in, s_out, server_side=True)

    def pump():
        s_in.write(c_out.read())
        c_in.write(s_out.read())

    for _ in range(10):
        for obj in (client, server):
            try:
                obj.do_handshake()
            except ssl.SSLWantReadError:
                pass
        pump()
    return client, server, pump


def test_read_into_bytearray_then_resize():
    # gh-5589: the ffi.from_buffer() export must be released when the call
    # returns, otherwise resizing the bytearray raises BufferError
    client, server, pump = _bio_pair()
    server.write(b"hello world")
    pump()
    buf = bytearray(64)
    n = client.read(64, buf)
    assert bytes(buf[:n]) == b"hello world"
    del buf[n:]
    assert buf == b"hello world"

    data = bytearray(b"again")
    server.write(data)
    del data[2:]
    pump()
    assert client.read(64) == b"again"


def test_memorybio_write_bytearray_then_resize():
    bio = ssl.MemoryBIO()
    data = bytearray(b"abcdef")
    bio.write(data)
    del data[3:]
    assert bio.read() == b"abcdef"


@pytest.mark.parametrize('name', ['sha256', 'sha3_256', 'blake2b'])
def test_hashlib_update_bytearray_then_resize(name):
    expected = hashlib.new(name, b"abcdef").hexdigest()
    data = bytearray(b"abcdef")
    h = hashlib.new(name)
    h.update(data)
    del data[3:]
    assert h.hexdigest() == expected
    data = bytearray(b"abcdef")
    h = hashlib.new(name, data)
    del data[3:]
    assert h.hexdigest() == expected
