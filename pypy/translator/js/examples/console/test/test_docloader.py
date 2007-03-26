
import py
from pypy.tool.udir import udir
from pypy.translator.js.examples.console.docloader import DocLoader

def test_load_html():
    tmpdir = udir.ensure("docloader", dir=1)
    help = tmpdir.ensure("one.html").write("<a href='dupa'>%s</a>")
    code = tmpdir.ensure("test_snippets2.py").write(str(py.code.Source('''
    class AppTest_one(object):
        def test_snippet_1(self):
            x = 1
    ''')) + '\n')
    ld = DocLoader(docdir=tmpdir, consoles=['one'], testfile=tmpdir.join('test_snippets2.py'))
    assert ld.get_html('one') == "<a href='dupa'>x = 1</a>"
    assert ld.get_snippet('one', 0) == 'x = 1'
