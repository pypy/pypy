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
from pypy.rpython.ootypesystem import ootype
from pypy.tool.udir import udir
from pypy.translator.js.log import log

from pypy.translator.js.asmgen import AsmGen
from pypy.translator.js.jts import JTS
from pypy.translator.js.opcodes import opcodes
from pypy.translator.js.function import Function
from pypy.translator.js.database import LowLevelDatabase

from pypy.translator.oosupport.genoo import GenOO

from heapq import heappush, heappop

def _path_join(root_path, *paths):
    path = root_path
    for p in paths:
        path = os.path.join(path, p)
    return path

class JS(GenOO):
    def __init__(self, translator, functions=[], stackless=False, compress=False, logging=False):
        backend_mapping = {
            'type_system_class' : JTS,
            'opcode_dict' : opcodes,
            'name_suffix' : '.js',
            'function_class' : Function,
            'database_class' : LowLevelDatabase,
            'asm_class' : AsmGen,
        }
        if not isinstance(functions, list):
            functions = [functions]
        GenOO.__init__(self, udir, translator, backend_mapping = backend_mapping, pending_graphs = [
            translator.annotator.bookkeeper.getdesc(f).cachedgraph(None) for f in functions ])
        self.translator = translator
        self.db.translator = translator
    
    def gen_pendings(self):
        while self.db._pending_nodes:
            node = self.db._pending_nodes.pop()
            to_render = []
            nparent = node
            while nparent.order != 0:
                nparent = nparent.parent
                to_render.append(nparent)
            to_render.reverse()
            for i in to_render:
                i.render(self.ilasm)
            
            node.render(self.ilasm)
    
    def generate_communication_proxy(self):
        """ Render necessary stuff aroundc communication
        proxies
        """
        for proxy in self.db.proxies:
            proxy.render(self.ilasm)
        
    def write_source(self):
        
        # write down additional functions
        # FIXME: when used with browser option it should probably
        # not be used as inlined, rather another script to load
        # this is just workaround
        
        self.generate_source()
        
        data = self.tmpfile.open().read()
        src_filename = _path_join(os.path.dirname(__file__), 'jssrc', 'misc.js')
        f = self.tmpfile.open("w")
        s = open(src_filename).read()
        f.write(s)
        self.ilasm = self.backend_mapping['asm_class'](f, self.assembly_name )
        self.generate_communication_proxy()
        f.write(data)
        f.close()
        
        self.filename = self.tmpfile
        
        return self.tmpfile
