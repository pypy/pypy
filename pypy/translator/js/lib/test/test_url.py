
from pypy.translator.js.lib.url import parse_url

def test_url():
    assert parse_url("path") == (["path"], {})
    assert parse_url("a/b/c/d") == (["a", "b", "c", "d"], {})
    assert parse_url("/a/b") == (["a", "b"], {})
    assert parse_url("/a/b/c/") == (["a", "b", "c"], {})
    assert parse_url("a/b?q=a&c=z") == (["a","b"], {"q":"a", "c":"z"})
    got = parse_url('/get_message?sid=2ed&pid=-1')
    assert got == (["get_message"], {'pid':'-1', 'sid':'2ed'})
