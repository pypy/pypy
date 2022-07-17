import _hashlib

def test_python_names():
    # these used to crash
    _hashlib.new("md5_sha1")
    _hashlib.new("sha512_224")
    _hashlib.new("sha512_256")
