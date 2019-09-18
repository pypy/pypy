from pytest import raises
import warnings

def test_bytes_invalid_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=DeprecationWarning)
        with raises(SyntaxError) as excinfo:
            eval("b'''\n\\z'''")
    assert not w
    assert excinfo.value.filename == '<string>'
