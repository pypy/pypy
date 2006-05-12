'''
reference material:
    http://webreference.com/javascript/reference/core_ref/
    http://webreference.com/programming/javascript/
    http://mochikit.com/
    http://www.mozilla.org/js/spidermonkey/
    svn co http://codespeak.net/svn/kupu/trunk/ecmaunit 
'''

import py
import os

from pypy.rpython.rmodel import inputconst
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype
from pypy.tool.udir import udir
from pypy.translator.js.node import Node
from pypy.translator.js.database import Database 
from pypy.translator.js.codewriter import CodeWriter
from pypy.translator.js.optimize import optimize_filesize
from pypy.translator.js.log import log
from pypy.translator.js import conftest

def _path_join(root_path, *paths):
    path = root_path
    for p in paths:
        path = os.path.join(path, p)
    return path

class JS(object):   # JS = Javascript
    def __init__(self, translator, functions=[], stackless=False, compress=False, logging=False):
        self.functions  = functions
        self.stackless  = stackless or conftest.option.jsstackless
        self.compress   = compress or conftest.option.jscompress
        self.logging    = logging or conftest.option.jslog
        self.db = Database(translator, self)

    def write_source(self):
        self.graph = []
        for  func in self.functions:
            bk   = self.db.translator.annotator.bookkeeper
            ptr  = getfunctionptr(bk.getdesc(func).getuniquegraph())
            c    = inputconst(lltype.typeOf(ptr), ptr)
            self.db.prepare_arg(c)
            self.graph.append( self.db.obj2node[c.value._obj].graph )

        # set up all nodes
        self.db.setup_all()

        self.filename = udir.join(func.func_name).new(ext='.js')
        f = open(str(self.filename),'w')
        codewriter = CodeWriter(f, self)

        codewriter.comment('filename: %s' % self.filename)
        codewriter.newline()

        src_filename = _path_join(os.path.dirname(__file__), 'src', 'misc.js')
        s = open(src_filename).read()
        f.write(s)

        codewriter.newline()
        for node in self.db.getnodes():
            node.write_implementation(codewriter)

        codewriter.comment('Forward declarations')
        codewriter.newline()
        for node in self.db.getnodes():
            node.write_forward_declaration(codewriter)
        codewriter.newline()

        codewriter.comment('Global array and strings data')
        codewriter.newline()
        for node in self.db.getnodes():
            node.write_global_array(codewriter)
        codewriter.newline()

        codewriter.comment('Global struct data')
        codewriter.newline()
        for node in self.db.getnodes():
            node.write_global_struct(codewriter)
        codewriter.newline()

        if self.stackless:
            s = 'll_stackless.js'
        else:
            s = 'stack.js'
        src_filename = _path_join(os.path.dirname(__file__), 'src', s)
        s = open(src_filename).read()
        if self.logging:
            s = s.replace('LOG', 'log')
        else:
            s = s.replace('LOG', '// log')
        f.write(s)

        f.close()

        if self.compress:
            optimize_filesize(str(self.filename))

        log('Written:', self.filename)
        return self.filename
