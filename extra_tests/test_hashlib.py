import hashlib

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
