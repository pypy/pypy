from pypy.translator.js.demo.jsdemo import example
from pypy.translator.js.examples import pythonconsole
from pypy.translator.js.demo.jsdemo.support import js_source

def test_example():
    example.build_http_server()
    try:
        source = js_source([example.runjs])
        assert 'function runjs ()' in source
    finally:
        example.httpd = None
        
def test_pythonconsole():
    pythonconsole.build_http_server()
    try:
        source = js_source([pythonconsole.setup_page])
        assert 'function setup_page ()' in source
    finally:
        pythonconsole.httpd = None
