from os.path import exists
use_boehm_gc = exists('/usr/lib/libgc.so') or exists('/usr/lib/libgc.a')

import os
import time
import types
import urllib

import py

from pypy.translator.llvm2 import build_llvm_module
from pypy.translator.llvm2.database import Database 
from pypy.translator.llvm2.pyxwrapper import write_pyx_wrapper 
from pypy.translator.llvm2.log import log
from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython import lltype
from pypy.tool.udir import udir
from pypy.translator.llvm2.codewriter import CodeWriter, \
     DEFAULT_INTERNAL, DEFAULT_TAIL, DEFAULT_CCONV
from pypy.translator.llvm2 import extfuncnode
from pypy.translator.llvm2.module.extfunction import extdeclarations, \
     extfunctions, gc_boehm, gc_disabled, dependencies
from pypy.translator.llvm2.node import LLVMNode

from pypy.translator.translator import Translator

from py.process import cmdexec 

function_count = {}

def get_ll(ccode, extern_dir, functions=[]):
    
    # goto codespeak and compile our c code
    request = urllib.urlencode({'ccode':ccode})
    llcode = urllib.urlopen('http://codespeak.net/pypy/llvm-gcc.cgi', request).read()

    # get rid of the struct that llvm-gcc introduces to struct types
    llcode = llcode.replace("%struct.", "%")

    #find function names, declare them internal with fastcc calling convertion
    ll_lines = []
    funcnames = {
        "%ll_frexp_result__Float_Signed"       : True,
        "%ll_modf_result__Float_Float"         : True,
        "%prepare_and_raise_ZeroDivisionError" : True,
        "%prepare_and_raise_OverflowError"     : True,
        "%prepare_and_raise_ValueError"        : True,
        "%prepare_and_raise_IOError"           : True,
        }
    for line in llcode.split('\n'):
        comment = line.find(';')
        if comment >= 0:
            line = line[:comment]
        line = line.rstrip()
        #if line[-1:] == '{':
        #   returntype, s = line.split(' ', 1)
        #   funcname  , s = s.split('(', 1)
        #   funcnames[funcname] = True
        #   line = '%s %s %s' % ("", DEFAULT_CCONV, line,)
        ll_lines.append(line)

    #patch calls to function that we just declared fastcc
    ll_lines2, calltag, declaretag = [], 'call ', 'declare '
    for line in ll_lines:
        i = line.find(calltag)
        if i >= 0:
            cconv = 'ccc'
            for funcname in funcnames.keys():
                if line.find(funcname) >= 0:
                    cconv = DEFAULT_CCONV
                    break
            line = "%scall %s %s" % (line[:i], cconv, line[i+len(calltag):])
        if line[:len(declaretag)] == declaretag:
            cconv = 'ccc'
            for funcname in funcnames.keys():
                if line.find(funcname) >= 0:
                    cconv = DEFAULT_CCONV
                    break
            line = "declare %s %s" % (cconv, line[len(declaretag):])
        ll_lines2.append(line)

    llcode = '\n'.join(ll_lines2)

    # create file
    llfilename = extern_dir.join("externs").new(ext='.ll')
    f = open(str(llfilename), 'w')
    f.write(llcode)
    f.close()

    # create bytecode
    os.chdir(str(extern_dir))
    cmdexec('llvm-as externs.ll')
    bcfilename = extern_dir.join("externs").new(ext='.bc')
    if functions:
        for func in functions:
            # extract
            cmdexec('llvm-extract -func %s -o %s.bc externs.bc' % (func, func))
        
        # link all the ll files
        functions_bcs = ' '.join(['%s.bc' % func for func in functions])
        cmdexec('llvm-link -o externs_linked.bc ' + functions_bcs)
        bcfilename = extern_dir.join("externs_linked").new(ext='.bc')
    
    return bcfilename
    
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

        rtyper = self.db._translator.rtyper
        from pypy.translator.c.extfunc import predeclare_all

        # hacks to make predeclare_all work
        self.db.standalone = True
        self.db.externalfuncs = {}
        decls = list(predeclare_all(self.db, rtyper))

        for c_name, obj in decls:
            if isinstance(obj, lltype.LowLevelType):
                print 'XXX1', c_name
                self.db.prepare_type(obj)
            elif isinstance(obj, types.FunctionType):
                print 'XXX2', c_name
                funcptr = getfunctionptr(self.translator, obj)
                c = inputconst(lltype.typeOf(funcptr), funcptr)
                self.db.prepare_arg_value(c)
            elif isinstance(lltype.typeOf(obj), lltype.Ptr):
                print 'XXX3', c_name
                self.db.prepare_constant(lltype.typeOf(obj), obj)
            else:
                assert False, "unhandled predeclare %s %s %s" % (c_name, type(obj), obj)

        return decls

    def generate_llfile(self, extern_decls):

        extern_dir = udir.join("externs")
        if extern_dir.check(dir=1):
            return
        extern_dir.mkdir()

        genllcode = ""

        def predeclarefn(c_name, llname):
            assert llname[0] == "%"
            assert '\n' not in llname
            return '#define\t%s\t%s' % (c_name, llname[1:])

        for c_name, obj in extern_decls:
            if isinstance(obj, lltype.LowLevelType):
                pass
            elif isinstance(obj, types.FunctionType):
                funcptr = getfunctionptr(self.translator, obj)
                c = inputconst(lltype.typeOf(funcptr), funcptr)
                llname = self.db.repr_arg(c)
                genllcode += predeclarefn(c_name, llname) + "\n"
            #elif isinstance(lltype.typeOf(obj), lltype.Ptr):
            #    if isinstance(obj.TO, lltype.FuncType):
            #        llname = self.db.repr_constant(obj)[1]
            #XXXXXXXXXXX        genllcode += predeclarefn(c_name, llname) + "\n"

        j = os.path.join
        p = j(j(os.path.dirname(__file__), "module"), "genexterns.c")
        math_fns  = 'acos asin atan ceil cos cosh exp fabs floor log log10 atan2 fmod '
        math_fns += 'sin sinh sqrt tan tanh frexp modf pow hypot ldexp is_error'
        fns = [('ll_math_%s' % f) for f in math_fns.split()]
        time_fns = "ll_time_time ll_time_clock ll_time_sleep ll_floattime"
        fns += time_fns.split()
        return get_ll(open(p).read(), extern_dir, fns)

    def gen_llvm_source(self, func=None):
        if self.debug:  print 'gen_llvm_source begin) ' + time.ctime()
        if func is None:
            func = self.translator.entrypoint
        self.entrypoint = func

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
        self.translator.rtyper.specialize_more_blocks()
        self.db.setup_all()

        self.generate_llfile(extern_decls)
 
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
        codewriter = CodeWriter(f, self.db.get_machine_word(), self.db.get_machine_uword())
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
        codewriter.append("    %%result = invoke %s %s%%%s to label %%no_exception except label %%exception" % (DEFAULT_CCONV, t[0], t[1]))
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
            extfuncnode.ExternalFuncNode.used_external_functions['%main'] = True

        extfuncnode.ExternalFuncNode.used_external_functions['%RPyString_FromString'] = True

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

        comment("End of file") ; nl()
        if self.debug:  print 'gen_llvm_source return) ' + time.ctime()
        return filename

    def create_module(self,
                      filename,
                      really_compile=True,
                      standalone=False,
                      optimize=False,
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
