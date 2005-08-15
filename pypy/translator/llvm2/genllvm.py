from os.path import exists
use_boehm_gc = exists('/usr/lib/libgc.so') or exists('/usr/lib/libgc.a')

import py
from pypy.translator.llvm2 import build_llvm_module
from pypy.translator.llvm2.database import Database 
from pypy.translator.llvm2.pyxwrapper import write_pyx_wrapper 
from pypy.translator.llvm2.log import log
from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython import lltype
from pypy.tool.udir import udir
from pypy.translator.llvm2.codewriter import CodeWriter
from pypy.translator.llvm2 import extfuncnode
from pypy.translator.llvm2.module.extfunction import extdeclarations, \
     extfunctions, gc_boehm, gc_disabled, dependencies
from pypy.translator.llvm2.node import LLVMNode

#XXX commented out because extfuncs temp. not working
#from pypy.rpython.module import ll_os, ll_time, ll_math, ll_strtod
#from pypy.rpython.annlowlevel import annotate_lowlevel_helper

from pypy.translator.translator import Translator

import time

function_count = {}

class GenLLVM(object):

    def __init__(self, translator, debug=True):
    
        # reset counters
        LLVMNode.nodename_count = {}    
        self.db = Database(translator)
        self.translator = translator
        translator.checkgraphs()
        extfuncnode.ExternalFuncNode.used_external_functions = {}

        # for debug we create comments of every operation that may be executed
        self.debug = debug

    def _add_to_database(self, name, funcptr):
        ptr = getfunctionptr(self.translator, func)
        c = inputconst(lltype.typeOf(funcptr), funcptr)
        c.value._obj.graph.name = name
        self.db.prepare_arg_value(c)

    def post_setup_externs(self):
        import types

        rtyper = self.db._translator.rtyper
        from pypy.translator.c.extfunc import predeclare_all

        # hacks to make predeclare_all work
        self.db.standalone = True
        self.db.externalfuncs = {}
        decls = list(predeclare_all(self.db, rtyper))

        for c_name, obj in decls:
            if isinstance(obj, lltype.LowLevelType):
                self.db.prepare_type(obj)
            elif isinstance(obj, types.FunctionType):
                funcptr = getfunctionptr(self.translator, obj)
                c = inputconst(lltype.typeOf(funcptr), funcptr)
                self.db.prepare_arg_value(c)

            elif isinstance(lltype.typeOf(obj), lltype.Ptr):
                self.db.prepare_constant(lltype.typeOf(obj), obj)
            else:
                print "XXX  predeclare" , c_name, type(obj), obj
                assert False

        return decls
                       
    def gen_llvm_source(self, func=None):
        if self.debug:  print 'gen_llvm_source begin) ' + time.ctime()
        if func is None:
            func = self.translator.entrypoint
        self.entrypoint = func

        #XXX commented out because extfuncs temp. not working
        # # make sure helper functions are available
        # rtyper = self.translator.rtyper
        # for ptr in (
        #             #rtyper.annotate_helper(ll_math.ll_frexp_result, [lltype.Float, lltype.Signed]),
        #             #rtyper.annotate_helper(ll_math.ll_modf_result , [lltype.Float, lltype.Float ]),
        #             rtyper.annotate_helper(ll_os.ll_stat_result   , [lltype.Signed] * 10),
        #            ):
        #     c = inputconst(lltype.typeOf(ptr), ptr)
        #     self.db.prepare_arg_value(c)

        # make sure exception matching and exception type are available
        # XXX Comment out anywat
        #e = self.translator.rtyper.getexceptiondata()
        #for ll_helper in (e.ll_exception_match, e.ll_raise_OSError):
        #    ptr = getfunctionptr(self.translator, ll_helper)
        #    c = inputconst(lltype.typeOf(ptr), ptr)
        #    self.db.prepare_arg_value(c)

        ptr = getfunctionptr(self.translator, func)
        c = inputconst(lltype.typeOf(ptr), ptr)
        entry_point = c.value._obj
        self.db.prepare_arg_value(c)

        #if self.debug:  print 'gen_llvm_source db.setup_all) ' + time.ctime()
        #7 minutes

        # set up all nodes
        self.db.setup_all()
        self.entrynode = self.db.set_entrynode(entry_point)

        # post set up externs
        extern_decls = self.post_setup_externs()
        self.db._translator.rtyper.specialize_more_blocks()
        self.db.setup_all()

        #if self.debug:  print 'gen_llvm_source typ_decl.writedatatypedecl) ' + time.ctime()
        #if self.debug:  print 'gen_llvm_source n_nodes) %d' % len(self.db.getnodes())
        #3 seconds
        #if self.debug:
        #    log.gen_llvm_source(self.db.dump_pbcs())
        
        # prevent running the same function twice in a test
        if func.func_name in function_count:
            postfix = '_%d' % function_count[func.func_name]
            function_count[func.func_name] += 1
        else:
            postfix = ''
            function_count[func.func_name] = 1
        filename = udir.join(func.func_name + postfix).new(ext='.ll')
        f = open(str(filename),'w')
        codewriter = CodeWriter(f)
        comment = codewriter.comment
        nl = codewriter.newline

        nl(); comment("Type Declarations"); nl()

        for c_name, obj in extern_decls:

            if isinstance(obj, lltype.LowLevelType):
                if isinstance(obj, lltype.Ptr):
                    obj = obj.TO
                l = "%%%s = type %s" % (c_name, self.db.repr_type(obj))
                codewriter.append(l)
            #XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX   
            #elif isinstance(obj, types.FunctionType):
            #    #c.value._obj.graph.name = c_name
            #    print "XXX  predeclare" , c_name, type(obj), obj

        for typ_decl in self.db.getnodes():
            typ_decl.writedatatypedecl(codewriter)

        if self.debug:  print 'gen_llvm_source typ_decl.writeglobalconstants) ' + time.ctime()
        #20 minutes
        nl(); comment("Global Data") ; nl()
        for typ_decl in self.db.getnodes():
            typ_decl.writeglobalconstants(codewriter)

        if self.debug:  print 'gen_llvm_source typ_decl.writecomments) ' + time.ctime()
        #0 minutes
        #if self.debug:
        #    nl(); comment("Comments") ; nl()
        #    for typ_decl in self.db.getnodes():
        #        typ_decl.writecomments(codewriter)
            
        if self.debug:  print 'gen_llvm_source extdeclarations) ' + time.ctime()
        nl(); comment("Function Prototypes") ; nl()
        for extdecl in extdeclarations.split('\n'):
            codewriter.append(extdecl)

        if self.debug:  print 'gen_llvm_source self._debug_prototype) ' + time.ctime()
        #if self.debug:
        #    self._debug_prototype(codewriter)
            
        if self.debug:  print 'gen_llvm_source typ_decl.writedecl) ' + time.ctime()
        for typ_decl in self.db.getnodes():
            typ_decl.writedecl(codewriter)

        if self.debug:  print 'gen_llvm_source boehm_gc) ' + time.ctime()
        nl(); comment("Function Implementation") 
        codewriter.startimpl()
        if use_boehm_gc:
            gc_funcs = gc_boehm
        else:
            gc_funcs = gc_disabled    
        for gc_func in gc_funcs.split('\n'):
            codewriter.append(gc_func)

        if self.debug:  print 'gen_llvm_source typ_decl.writeimpl) ' + time.ctime()
        #XXX ? minutes
        for typ_decl in self.db.getnodes():
            typ_decl.writeimpl(codewriter)

        if self.debug:  print 'gen_llvm_source used_external_functions) ' + time.ctime()
        depdone = {}
        for funcname,value in extfuncnode.ExternalFuncNode.used_external_functions.iteritems():
            deps = dependencies(funcname,[])
            deps.reverse()
            for dep in deps:
                if dep not in depdone:
                    try:
                        llvm_code = extfunctions[dep][1]
                    except KeyError:
                        msg = 'primitive function %s has no implementation' % dep
                        codewriter.comment('XXX: Error: ' + msg)
                        #raise Exception('primitive function %s has no implementation' %(dep,))
                        continue
                    for extfunc in llvm_code.split('\n'):
                        codewriter.append(extfunc)
                    depdone[dep] = True

        if self.debug:  print 'gen_llvm_source entrypoint) ' + time.ctime()
        #XXX use codewriter methods here
        decl = self.entrynode.getdecl()
        t = decl.split('%', 1)
        if t[0] == 'double ':   #XXX I know, I know... refactor at will!
            no_result = '0.0'
        elif t[0] == 'bool ':
            no_result = 'false'
        else:
            no_result = '0'
        codewriter.newline()
        codewriter.append("ccc %s%%__entrypoint__%s {" % (t[0], t[1]))
        codewriter.append("    %%result = invoke fastcc %s%%%s to label %%no_exception except label %%exception" % (t[0], t[1]))
        codewriter.newline()
        codewriter.append("no_exception:")
        codewriter.append("    store %RPYTHON_EXCEPTION_VTABLE* null, %RPYTHON_EXCEPTION_VTABLE** %last_exception_type")
        codewriter.append("    ret %s%%result" % t[0])
        codewriter.newline()
        codewriter.append("exception:")
        codewriter.append("    ret %s%s" % (t[0], no_result))
        codewriter.append("}")
        codewriter.newline()
        codewriter.append("ccc int %__entrypoint__raised_LLVMException() {")
        codewriter.append("    %tmp    = load %RPYTHON_EXCEPTION_VTABLE** %last_exception_type")
        codewriter.append("    %result = cast %RPYTHON_EXCEPTION_VTABLE* %tmp to int")
        codewriter.append("    ret int %result")
        codewriter.append("}")
        codewriter.newline()
        # XXX we need to create our own main() that calls the actual entry_point function
        entryfunc_name = t[1].split('(')[0]
        if entryfunc_name != 'main' and entryfunc_name == 'entry_point': #XXX just to get on with translate_pypy
            codewriter.append("int %main() {")
            codewriter.append("    %argv = call fastcc %structtype.list* %ll_newlist__listPtrConst_Signed.2(int 0)")
            codewriter.append("    %ret  = call fastcc int %entry_point(%structtype.list* %argv)")
            codewriter.append("    ret int %ret")
            codewriter.append("}")
            codewriter.newline()

        comment("End of file") ; nl()
        if self.debug:  print 'gen_llvm_source return) ' + time.ctime()
        return filename

    def create_module(self,
                      filename,
                      really_compile=True,
                      standalone=False,
                      optimize=False,   #XXX disabled because it breaks things (debug output)
                      exe_name=None):

        if not llvm_is_on_path():
            # XXX not good to call py.test.skip here
            py.test.skip("llvm not found")

        if standalone:
            return build_llvm_module.make_module_from_llvm(filename,
                                                           optimize=optimize,
                                                           exe_name=exe_name)
        else:
            postfix = ''
            basename = filename.purebasename+'_wrapper'+postfix+'.pyx'
            pyxfile = filename.new(basename = basename)
            write_pyx_wrapper(self.entrynode, pyxfile)    
            return build_llvm_module.make_module_from_llvm(filename,
                                                           pyxfile=pyxfile,
                                                           optimize=optimize)

    def _debug_prototype(self, codewriter):
        codewriter.append("declare int %printf(sbyte*, ...)")

def genllvm(translator, log_source=False, **kwds):
    gen = GenLLVM(translator)
    filename = gen.gen_llvm_source()
    if log_source:
        log.genllvm(open(filename).read())
    return gen.create_module(filename, **kwds)

def llvm_is_on_path():
    try:
        py.path.local.sysfind("llvm-as")
    except py.error.ENOENT: 
        return False 
    return True

def compile_module(function, annotation, view=False, **kwds):
    t = Translator(function)
    a = t.annotate(annotation)
    t.specialize()
    if view:
        t.view()
    return genllvm(t, **kwds)

def compile_function(function, annotation, **kwds):
    mod = compile_module(function, annotation, **kwds)
    return getattr(mod, function.func_name + "_wrapper")

def compile_module_function(function, annotation, **kwds):
    mod = compile_module(function, annotation, **kwds)
    f = getattr(mod, function.func_name + "_wrapper")
    return mod, f
