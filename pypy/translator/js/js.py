'''
reference material:
    http://webreference.com/javascript/reference/core_ref/
    http://webreference.com/programming/javascript/
    http://mochikit.com/
    
'''

#import os
#import time
#import types
#import urllib

import py

from pypy.translator.llvm.database import Database 
from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython import lltype
from pypy.tool.udir import udir
from pypy.translator.js.codewriter import CodeWriter
from pypy.translator.js.gc import GcPolicy
from pypy.translator.js.exception import ExceptionPolicy
from pypy.translator.js.log import log


class JS(object):   # JS = Javascript
    function_count = {}
    
    def __init__(self, translator, function=None, gcpolicy=None, exceptionpolicy=None, debug=False):
        self.db = Database(self, translator)
        self.translator = translator
        self.gcpolicy = GcPolicy.new(gcpolicy)
        self.exceptionpolicy = ExceptionPolicy.new(exceptionpolicy)
        #extfuncnode.ExternalFuncNode.used_external_functions = {}
        self.debug = debug # for debug we create comments of every operation that may be executed
        if debug:
            translator.checkgraphs()

        if function is None:
            function= self.translator.entrypoint
        self.entrypoint = function

        self.filename = self.wrapper_filename = None

    def write_source(self):
        func = self.entrypoint
        ptr = getfunctionptr(self.translator, func)
        c = inputconst(lltype.typeOf(ptr), ptr)
        entry_point = c.value._obj
        self.db.prepare_arg_value(c)

        # set up all nodes
        self.db.setup_all()
        self.entrynode = self.db.set_entrynode(entry_point)
        entryfunc_name = self.entrynode.getdecl().split('%', 1)[1].split('(')[0]

        ## post set up externs
        #extern_decls = post_setup_externs(self.db)
        #self.translator.rtyper.specialize_more_blocks()
        #self.db.setup_all()
        #using_external_functions = extfuncnode.ExternalFuncNode.used_external_functions.keys() != []
        #
        #support_functions = "%raisePyExc_IOError %raisePyExc_ValueError "\
        #                    "%raisePyExc_OverflowError %raisePyExc_ZeroDivisionError "\
        #                    "%prepare_ZeroDivisionError %prepare_OverflowError %prepare_ValueError "\
        #                    "%RPyString_FromString %RPyString_AsString %RPyString_Size".split()
        #
        #global llexterns_header, llexterns_functions
        #if llexterns_header is None and using_external_functions:
        #    llexterns_header, llexterns_functions = generate_llfile(self.db, extern_decls, support_functions, self.debug)
 
        # prevent running the same function twice in a test
        if func.func_name in self.function_count:
            postfix = '_%d' % self.function_count[func.func_name]
            self.function_count[func.func_name] += 1
        else:
            postfix = ''
            self.function_count[func.func_name] = 1
        self.filename = udir.join(func.func_name + postfix).new(ext='.js')
        f = open(str(self.filename),'w')
        codewriter = CodeWriter(f, self)
        comment = codewriter.comment
        nl = codewriter.newline

        #if using_external_functions:
        #    nl(); comment("External Function Declarations") ; nl()
        #    codewriter.append(llexterns_header)

        nl(); comment("Type Declarations"); nl()
        #for c_name, obj in extern_decls:
        #    if isinstance(obj, lltype.LowLevelType):
        #        if isinstance(obj, lltype.Ptr):
        #            obj = obj.TO
        #        l = "%%%s = type %s" % (c_name, self.db.repr_type(obj))
        #        codewriter.append(l)

        for typ_decl in self.db.getnodes():
            typ_decl.writedatatypedecl(codewriter)

        nl(); comment("Global Data") ; nl()
        for typ_decl in self.db.getnodes():
            typ_decl.writeglobalconstants(codewriter)

        nl(); comment("Function Prototypes") ; nl()
        #codewriter.append(extdeclarations)
        #codewriter.append(self.gcpolicy.declarations())

        for typ_decl in self.db.getnodes():
            typ_decl.writedecl(codewriter)

        nl(); comment("Function Implementation") 
        codewriter.startimpl()
        
        for typ_decl in self.db.getnodes():
            typ_decl.writeimpl(codewriter)

        #codewriter.append(self.exceptionpolicy.llvmcode(self.entrynode))
        #
        ## XXX we need to create our own main() that calls the actual entry_point function
        #if entryfunc_name == 'pypy_entry_point': #XXX just to get on with translate_pypy
        #    extfuncnode.ExternalFuncNode.used_external_functions['%main'] = True
        #
        #elif entryfunc_name == 'pypy_main_noargs': #XXX just to get on with bpnn & richards
        #    extfuncnode.ExternalFuncNode.used_external_functions['%main_noargs'] = True
        #
        #for f in support_functions:
        #    extfuncnode.ExternalFuncNode.used_external_functions[f] = True
        #
        #depdone = {}
        #for funcname,value in extfuncnode.ExternalFuncNode.used_external_functions.iteritems():
        #    deps = dependencies(funcname,[])
        #    deps.reverse()
        #    for dep in deps:
        #        if dep not in depdone:
        #            if dep in extfunctions: #else external function that is shared with genc
        #                codewriter.append(extfunctions[dep][1])
        #            depdone[dep] = True
        #
        #if using_external_functions:
        #    nl(); comment("External Function Implementation") ; nl()
        #    codewriter.append(llexterns_functions)

        comment("Wrapper code for the Javascript CLI") ; nl()
        graph        = self.db.entrynode.graph
        startblock  = graph.startblock
        args        = ','.join(['arguments[%d]' % i for i,v in enumerate(startblock.inputargs)])
        wrappercode = 'pypy_%s(%s);\n' % (graph.name, args)
        codewriter.indent(wrappercode)

        comment("End of file") ; nl()
        log('Written:', self.filename)
        return self.filename
