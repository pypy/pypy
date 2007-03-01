from pypy.lang.js.jsparser import read_js_output, JsSyntaxError, parse
from pypy.lang.js.test.test_interp import js_is_on_path
import py

js_is_on_path()


def test_quoting():
    read_js_output('x = "\'"')
    read_js_output('x = "\\\\"')