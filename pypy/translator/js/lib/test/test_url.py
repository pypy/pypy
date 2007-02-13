
from pypy.translator.js.lib.url import parse_url

def test_url():
    assert parse_url("path") == (["path"], {})
    assert parse_url("a/b/c/d") == (["a", "b", "c", "d"], {})
    assert parse_url("/a/b") == (["a", "b"], {})
    assert parse_url("/a/b/c/") == (["a", "b", "c"], {})
    assert parse_url("a/b?q=a&c=z") == (["a","b"], {"q":"a", "c":"z"})

