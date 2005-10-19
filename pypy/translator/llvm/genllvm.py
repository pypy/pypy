import os
import time
import types
import urllib

import py

from pypy.translator.llvm import build_llvm_module
from pypy.translator.llvm.database import Database 
from pypy.translator.llvm.pyxwrapper import write_pyx_wrapper 
from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython import lltype
from pypy.tool.udir import udir
from pypy.translator.llvm.codewriter import CodeWriter, \
     DEFAULT_TAIL, DEFAULT_CCONV
from pypy.translator.llvm import extfuncnode
from pypy.translator.llvm.module.extfunction import extdeclarations, \
     extfunctions, dependencies
from pypy.translator.llvm.node import LLVMNode
from pypy.translator.llvm.structnode import StructNode
from pypy.translator.llvm.externs2ll import post_setup_externs, generate_llfile
from pypy.translator.llvm.gc import GcPolicy
from pypy.translator.llvm.exception import ExceptionPolicy
from pypy.translator.translator import Translator

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("llvm")
log.setconsumer("llvm", ansi_log)

function_count = {}
llexterns_header = llexterns_functions = None


class GenLLVM(object):

    def __init__(self, translator, gcpolicy=None, exceptionpolicy=None, debug=False):
    
        # reset counters
        LLVMNode.nodename_count = {}    
        self.db = Database(self, translator)
        self.translator = translator
        self.gcpolicy = gcpolicy
        self.exceptionpolicy = exceptionpolicy
        extfuncnode.ExternalFuncNode.used_external_functions = {}
        self.debug = debug # for debug we create comments of every operation that may be executed
        if debug:
            translator.checkgraphs()

    def _checkpoint(self, msg=None):
        if self.debug:
            if msg:
                t = (time.time() - self.starttime)
                log('\t%s took %02dm%02ds' % (msg, t/60, t%60))
            else:
                log('GenLLVM:')
            self.starttime = time.time()

    def _print_node_stats(self):
        """run_pypy-llvm.sh [aug 29th 2005]
        before slotifying: 350Mb
        after  slotifying: 300Mb, 35 minutes until the .ll file is fully written.
        STATS (1, "<class 'pypy.translator.llvm.arraynode.VoidArrayTypeNode'>")
        STATS (1, "<class 'pypy.translator.llvm.opaquenode.OpaqueTypeNode'>")
        STATS (9, "<class 'pypy.translator.llvm.structnode.StructVarsizeTypeNode'>")
        STATS (46, "<class 'pypy.translator.llvm.extfuncnode.ExternalFuncNode'>")
        STATS (52, "<class 'pypy.translator.llvm.arraynode.ArrayTypeNode'>")
        STATS (189, "<class 'pypy.translator.llvm.arraynode.VoidArrayNode'>")
        STATS (819, "<class 'pypy.translator.llvm.opaquenode.OpaqueNode'>")
        STATS (1250, "<class 'pypy.translator.llvm.funcnode.FuncTypeNode'>")
        STATS (1753, "<class 'pypy.translator.llvm.structnode.StructTypeNode'>")
        STATS (5896, "<class 'pypy.translator.llvm.funcnode.FuncNode'>")
        STATS (24013, "<class 'pypy.translator.llvm.arraynode.ArrayNode'>")
        STATS (25411, "<class 'pypy.translator.llvm.structnode.StructVarsizeNode'>")
        STATS (26210, "<class 'pypy.translator.llvm.arraynode.StrArrayNode'>")
        STATS (268884, "<class 'pypy.translator.llvm.structnode.StructNode'>")
        """
        return #disable node stats output
        if not self.debug:
            return
        nodecount = {}
        for node in self.db.getnodes():
            typ = type(node)
            try:
                nodecount[typ] += 1
            except:
                nodecount[typ] = 1
        stats = [(count, str(typ)) for typ, count in nodecount.iteritems()]
        stats.sort()
        for s in stats:
            log('STATS %s' % str(s))

    def gen_llvm_source(self, func=None):
        """
        init took 00m00s
        setup_all took 08m14s
        setup_all externs took 00m00s
        generate_ll took 00m02s
        write externs type declarations took 00m00s
        write data type declarations took 00m02s
        write global constants took 09m49s
        write function prototypes took 00m00s
        write declarations took 00m03s
        write implementations took 01m54s
        write support functions took 00m00s
        write external functions took 00m00s
        """
        self._checkpoint()

        if func is None:
            func = self.translator.entrypoint
        self.entrypoint = func

        ptr = getfunctionptr(self.translator, func)
        c = inputconst(lltype.typeOf(ptr), ptr)
        entry_point = c.value._obj
        self.db.prepare_arg_value(c)
        self._checkpoint('init')

        # set up all nodes
        self.db.setup_all()
        self.entrynode = self.db.set_entrynode(entry_point)
        entryfunc_name = self.entrynode.getdecl().split('%', 1)[1].split('(')[0]
        self._checkpoint('setup_all')

        # post set up externs
        extern_decls = post_setup_externs(self.db)
        self.translator.rtyper.specialize_more_blocks()
        self.db.setup_all()
        using_external_functions = extfuncnode.ExternalFuncNode.used_external_functions.keys() != []
        self._print_node_stats()
        self._checkpoint('setup_all externs')

        support_functions = "%raisePyExc_IOError %raisePyExc_ValueError "\
                            "%raisePyExc_OverflowError %raisePyExc_ZeroDivisionError "\
                            "%raisePyExc_RuntimeError "\
                            "%prepare_ZeroDivisionError %prepare_OverflowError %prepare_ValueError "\
                            "%RPyString_FromString %RPyString_AsString %RPyString_Size".split()

        global llexterns_header, llexterns_functions
        if llexterns_header is None and using_external_functions:
            llexterns_header, llexterns_functions = generate_llfile(self.db, extern_decls, support_functions, self.debug)
            self._checkpoint('generate_ll')
 
        # prevent running the same function twice in a test
        if func.func_name in function_count:
            postfix = '_%d' % function_count[func.func_name]
            function_count[func.func_name] += 1
        else:
            postfix = ''
            function_count[func.func_name] = 1
        filename = udir.join(func.func_name + postfix).new(ext='.ll')
        f = open(str(filename),'w')
        codewriter = CodeWriter(f, self)
        comment = codewriter.comment
        nl = codewriter.newline

        if using_external_functions:
            nl(); comment("External Function Declarations") ; nl()
            codewriter.append(llexterns_header)

        nl(); comment("Type Declarations"); nl()
        for c_name, obj in extern_decls:
            if isinstance(obj, lltype.LowLevelType):
                if isinstance(obj, lltype.Ptr):
                    obj = obj.TO
                l = "%%%s = type %s" % (c_name, self.db.repr_type(obj))
                codewriter.append(l)
        self._checkpoint('write externs type declarations')

        for typ_decl in self.db.getnodes():
            typ_decl.writedatatypedecl(codewriter)
        self._checkpoint('write data type declarations')

        nl(); comment("Global Data") ; nl()
        for typ_decl in self.db.getnodes():
            typ_decl.writeglobalconstants(codewriter)
        self._checkpoint('write global constants')

        nl(); comment("Function Prototypes") ; nl()
        codewriter.append(extdeclarations)
        codewriter.append(self.gcpolicy.declarations())
        self._checkpoint('write function prototypes')

        for typ_decl in self.db.getnodes():
            typ_decl.writedecl(codewriter)
        self._checkpoint('write declarations')

        nl(); comment("Function Implementation") 
        codewriter.startimpl()
        
        for typ_decl in self.db.getnodes():
            typ_decl.writeimpl(codewriter)
        self._checkpoint('write implementations')

        codewriter.append(self.exceptionpolicy.llvmcode(self.entrynode))

        # XXX we need to create our own main() that calls the actual entry_point function
        if entryfunc_name == 'pypy_entry_point': #XXX just to get on with translate_pypy
            extfuncnode.ExternalFuncNode.used_external_functions['%main'] = True

        elif entryfunc_name == 'pypy_main_noargs': #XXX just to get on with bpnn & richards
            extfuncnode.ExternalFuncNode.used_external_functions['%main_noargs'] = True

        for f in support_functions:
            extfuncnode.ExternalFuncNode.used_external_functions[f] = True

        depdone = {}
        for funcname,value in extfuncnode.ExternalFuncNode.used_external_functions.iteritems():
            deps = dependencies(funcname,[])
            deps.reverse()
            for dep in deps:
                if dep not in depdone:
                    if dep in extfunctions: #else external function that is shared with genc
                        codewriter.append(extfunctions[dep][1])
                    depdone[dep] = True
        self._checkpoint('write support functions')
        
        if using_external_functions:
            nl(); comment("External Function Implementation") ; nl()
            codewriter.append(llexterns_functions)
        self._checkpoint('write external functions')

        comment("End of file") ; nl()
        return filename

    def create_module(self,
                      filename,
                      really_compile=True,
                      standalone=False,
                      optimize=True,
                      exe_name=None):

        if standalone:
            return build_llvm_module.make_module_from_llvm(self, filename,
                                                           optimize=optimize,
                                                           exe_name=exe_name)
        else:
            postfix = ''
            basename = filename.purebasename + '_wrapper' + postfix + '.pyx'
            pyxfile = filename.new(basename = basename)
            write_pyx_wrapper(self, pyxfile)    
            return build_llvm_module.make_module_from_llvm(self, filename,
                                                           pyxfile=pyxfile,
                                                           optimize=optimize)


def genllvm(translator, gcpolicy=None, exceptionpolicy=None, log_source=False, **kwds):
    gen = GenLLVM(translator, GcPolicy.new(gcpolicy), ExceptionPolicy.new(exceptionpolicy))
    filename = gen.gen_llvm_source()
    if log_source:
        log(open(filename).read())
    return gen.create_module(filename, **kwds)

def compile_module(function, annotation, view=False, **kwds):
    t = Translator(function)
    a = t.annotate(annotation)
    a.simplify()
    t.specialize()
    t.backend_optimizations(ssa_form=False)
    if view:    #note: this is without policy transforms
        t.view()
    return genllvm(t, **kwds)

def compile_function(function, annotation, **kwds):
    mod = compile_module(function, annotation, **kwds)
    return getattr(mod, 'pypy_' + function.func_name + "_wrapper")
