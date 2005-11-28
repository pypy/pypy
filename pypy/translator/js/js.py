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

from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython.lltypesystem import lltype
from pypy.tool.udir import udir
from pypy.translator.js.node import Node
from pypy.translator.js.database import Database 
from pypy.translator.js.codewriter import CodeWriter
from pypy.translator.js.log import log
from pypy.translator.js import conftest

def _path_join(root_path, *paths):
    path = root_path
    for p in paths:
        path = os.path.join(path, p)
    return path

class JS(object):   # JS = Javascript
    def __init__(self, translator, entrypoint=None, stackless=False):
        self.db = Database(translator)
        self.entrypoint = entrypoint or translator.entrypoint
        self.stackless = stackless or conftest.option.jsstackless

    def write_source(self):
        func = self.entrypoint
        ptr  = getfunctionptr(self.db.translator, func)
        c    = inputconst(lltype.typeOf(ptr), ptr)
        self.db.prepare_arg_value(c)

        #add exception matching function (XXX should only be done when needed)
        e          = self.db.translator.rtyper.getexceptiondata()
        matchptr   = getfunctionptr(self.db.translator, e.ll_exception_match)
        matchconst = inputconst(lltype.typeOf(matchptr), matchptr)
        self.db.prepare_arg_value(matchconst)

        # set up all nodes
        self.db.setup_all()

        self.filename = udir.join(func.func_name).new(ext='.js')
        f = open(str(self.filename),'w')
        codewriter = CodeWriter(f, self)

        codewriter.comment('filename: %s' % self.filename)
        codewriter.newline()
        for node in self.db.getnodes():
            node.write_implementation(codewriter)

        codewriter.comment('Forward struct declarations')
        codewriter.newline()
        for node in self.db.getnodes():
            node.write_forward_struct_declaration(codewriter)
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
        f.write(open(src_filename).read())

        f.close()

        entry_point= c.value._obj
        self.graph = self.db.obj2node[entry_point].graph
        startblock = self.graph.startblock
        args       = ','.join(['arguments[%d]' % i for i,v in enumerate(startblock.inputargs)])
        if self.stackless:
            self.wrappertemplate = "load('%s'); print(slp_entry_point('%s(%%s)'))" % (self.filename, self.graph.name)
        else:
            self.wrappertemplate = "load('%s'); print(%s(%%s))" % (self.filename, self.graph.name)

        log('Written:', self.filename)
        return self.filename
