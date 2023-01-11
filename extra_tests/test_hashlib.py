import hashlib

def test_python_names():
    for algo in hashlib.algorithms_available:
        hashlib.new(algo)
    # these used to crash
    hashlib.new("md5_sha1")
    hashlib.new("sha512_224")
    hashlib.new("sha512_256")
