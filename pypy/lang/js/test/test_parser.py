from pypy.lang.js.jsparser import read_js_output, JsSyntaxError, parse
from pypy.lang.js.test.test_interp import js_is_on_path
import py


if not js_is_on_path():
    py.test.skip("js binary not found")


def test_read_js_output():
    assert read_js_output("1+1").find("PLUS") > -1
    assert read_js_output("""
    function f(x) {
        return (x);
    }
    """).find("RETURN") != -1
    py.test.raises(JsSyntaxError, "read_js_output(\"1+\")")
    py.test.raises(JsSyntaxError, "read_js_output(\"xx xxx\")")

def test_simple_parse():
    data = parse("1+1")
    assert data['type'] == 'SCRIPT'
    assert data['0']['type'] == 'SEMICOLON'
    data = parse("function s(x) { return 1;}")
    assert data['0']['body']['0']['value']['value'] == '1'
    assert sorted(data.keys()) == ['0', 'funDecls', 'length', 'lineno', \
                                  'tokenizer', 'type', 'varDecls']

def test_single_quote():
    "test if parser eats single quotes"
    data = parse("x = '2'")
    assert data['type'] == 'SCRIPT'
