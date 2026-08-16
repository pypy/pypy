import hashlib
import pytest

def test_python_names():
    for algo in hashlib.algorithms_available:
        hashlib.new(algo)
    # these used to crash
    hashlib.new("md5_sha1")
    hashlib.new("sha512_224")
    hashlib.new("sha512_256")

def test_large_hmac():
    # issue 3962: problem with large msg code path
    import hmac
    m  = hmac.HMAC(b'', msg=b'0'*2049, digestmod='sha256')
    assert len(m.digest()) == 32

def test_crash():
    # issue 5127
    with pytest.raises((AttributeError, TypeError)):
        hashlib.shake_128()._keccak_init(())

def test_hmac_digest_buffers():
    # issue 5544: key and msg accept any bytes-like object
    import hmac
    expected = hmac.digest(b'key', b'msg', 'sha256')
    for key in [b'key', bytearray(b'key'), memoryview(b'key')]:
        for msg in [b'msg', bytearray(b'msg'), memoryview(b'msg')]:
            assert hmac.digest(key, msg, 'sha256') == expected

def test_hmac_digest_itemsize():
    # issue 5544: the length is in bytes, not in items
    import array
    import hmac
    msg = array.array('i', [1, 2])
    assert hmac.digest(b'key', msg, 'sha256') == \
           hmac.digest(b'key', msg.tobytes(), 'sha256')


