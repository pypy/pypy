
from pypy.translator.js.lib.support import js_source
from pypy.translator.js.modules.mochikit import *

class TestRender(object):
    def test_escape_html(self):
        def x():
            escapeHTML("xxx") + "xxx"
        assert js_source([x], use_pdb=False).find("escapeHTML (") != -1

    def test_serialize_json(self):
        def x():
            return serializeJSON(3) + serializeJSON("aaa") + serializeJSON([1])
        assert js_source([x])
