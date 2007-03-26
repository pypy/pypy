
""" Simple module for loading documentation of various
pypy-cs from doc directory
"""

import py

class DocLoader(object):
    def __init__(self, consoles, docdir, testfile):
        self.consoles = consoles
        self.docdir = py.path.local(docdir)
        assert self.docdir.check(dir=1)
        self.testfile = testfile
        assert self.testfile.check()
        self.htmls = {}
        self.snippets = {}
        self.load()

    def get_html(self, console):
        return self.htmls[console]

    def get_snippet(self, console, num):
        return str(self.snippets[console][num])

    def load(self):
        def mangle_name(name):
            return name.replace("-", "_").replace(".", "_")

        def mangle(source):
            source = source.strip()
            del source.lines[0]
            return source.deindent()
        
        testmod = self.testfile.pyimport()
        for console in self.consoles:
            html = self.docdir.join(console + '.html').read()
            snip_class = getattr(testmod, 'AppTest_' + mangle_name(console))
            snippets = [mangle(py.code.Source(getattr(snip_class, name)))
                        for name in
                        dir(snip_class) if name.startswith("test_snippet")]
            self.snippets[console] = snippets
            self.htmls[console] = html % tuple([str(i) for i in snippets])

