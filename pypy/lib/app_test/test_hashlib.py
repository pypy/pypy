from pypy.lib import hashlib, _hashlib

def test_unicode():
    assert isinstance(hashlib.new('sha1', u'xxx'), _hashlib.hash)
