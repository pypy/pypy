from os.path import exists
use_boehm_gc = exists('/usr/lib/libgc.so') or exists('/usr/lib/libgc.a')

import os
import time
import types
import urllib

import py

from pypy.translator.llvm import build_llvm_module
from pypy.translator.llvm.database import Database 
from pypy.translator.llvm.pyxwrapper import write_pyx_wrapper 
from pypy.translator.llvm.log import log
from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython import lltype
from pypy.tool.udir import udir
from pypy.translator.llvm.codewriter import CodeWriter, \
     DEFAULT_INTERNAL, DEFAULT_TAIL, DEFAULT_CCONV
from pypy.translator.llvm import extfuncnode
from pypy.translator.llvm.module.extfunction import extdeclarations, \
     extfunctions, gc_boehm, gc_disabled, dependencies
from pypy.translator.llvm.node import LLVMNode

from pypy.translator.translator import Translator

from py.process import cmdexec 

function_count = {}
llcode_header = ll_functions = None

ll_func_names = [
       "%prepare_and_raise_IOError",
       "%prepare_and_raise_ValueError",
       "%prepare_and_raise_OverflowError",
       "%prepare_and_raise_ZeroDivisionError",
       "%RPyString_AsString",
       "%RPyString_FromString",
       "%RPyString_Size"]
       
def get_ll(ccode, function_names):

    # goto codespeak and compile our c code
    request = urllib.urlencode({'ccode':ccode})
    llcode = urllib.urlopen('http://codespeak.net/pypy/llvm-gcc.cgi', request).read()

    # strip lines
    ll_lines = []
    function_names = list(function_names) + ll_func_names
    funcnames = dict([(k, True) for k in function_names])

    # strip declares tjat in ll_func_names
    for line in llcode.split('\n'):

        # get rid of any of the structs that llvm-gcc introduces to struct types
        line = line.replace("%struct.", "%")

        # strip comments
        comment = line.find(';')
        if comment >= 0:
            line = line[:comment]
        line = line.rstrip()

        # find function names, declare them internal with fastcc calling convertion
        if line[-1:] == '{':
           returntype, s = line.split(' ', 1)
           funcname  , s = s.split('(', 1)
           funcnames[funcname] = True
	   assert line.find("internal") == -1
           line = '%s %s %s' % ("", DEFAULT_CCONV, line,)
        ll_lines.append(line)

    # patch calls to function that we just declared fastcc
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
    global llcode_header, ll_functions 
    llcode_header, ll_functions = llcode.split('implementation')
    
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
                self.db.prepare_type(obj)
            elif isinstance(obj, types.FunctionType):
                funcptr = getfunctionptr(self.translator, obj)
                c = inputconst(lltype.typeOf(funcptr), funcptr)
                self.db.prepare_arg_value(c)
            elif isinstance(lltype.typeOf(obj), lltype.Ptr):
                self.db.prepare_constant(lltype.typeOf(obj), obj)
            else:
                assert False, "unhandled predeclare %s %s %s" % (c_name, type(obj), obj)

        return decls

    def generate_llfile(self, extern_decls):
        ccode = []
        function_names = []

        def predeclarefn(c_name, llname):
            function_names.append(llname)
            assert llname[0] == "%"
            llname = llname[1:]
            assert '\n' not in llname
            ccode.append('#define\t%s\t%s\n' % (c_name, llname))
            
        for c_name, obj in extern_decls:
            if isinstance(obj, lltype.LowLevelType):
                s = "#define %s struct %s\n%s;\n" % (c_name, c_name, c_name)
                ccode.append(s)
            elif isinstance(obj, types.FunctionType):
                funcptr = getfunctionptr(self.translator, obj)
                c = inputconst(lltype.typeOf(funcptr), funcptr)
                predeclarefn(c_name, self.db.repr_arg(c))
            elif isinstance(lltype.typeOf(obj), lltype.Ptr):
                if isinstance(lltype.typeOf(obj._obj), lltype.FuncType):
                    predeclarefn(c_name, self.db.repr_name(obj._obj))

        # append local file
        j = os.path.join
        p = j(j(os.path.dirname(__file__), "module"), "genexterns.c")
        ccode.append(open(p).read())

        get_ll("".join(ccode), function_names)

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

        if llcode_header is None:
            self.generate_llfile(extern_decls)
        lldeclarations, llimplementation = llcode_header, ll_functions
 
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

        nl(); comment("EXTERNAL FUNCTION DECLARATIONS") ; nl()
        for s in lldeclarations.split('\n'):
            codewriter.append(s)

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
        if entryfunc_name == 'pypy_entry_point': #XXX just to get on with translate_pypy
            extfuncnode.ExternalFuncNode.used_external_functions['%main'] = True

        elif entryfunc_name == 'pypy_main_noargs': #XXX just to get on with bpnn & richards
            extfuncnode.ExternalFuncNode.used_external_functions['%main_noargs'] = True

        for f in "prepare_and_raise_OverflowError prepare_and_raise_ValueError "\
	         "prepare_and_raise_ZeroDivisionError prepare_and_raise_IOError "\
                 "prepare_ZeroDivisionError prepare_OverflowError prepare_ValueError "\
		 "RPyString_FromString RPyString_AsString RPyString_Size".split():
            extfuncnode.ExternalFuncNode.used_external_functions["%" + f] = True

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

        nl(); comment("EXTERNAL FUNCTION IMPLEMENTATION") ; nl()
        for s in llimplementation.split('\n'):
            codewriter.append(s)

        comment("End of file") ; nl()
        if self.debug:  print 'gen_llvm_source return) ' + time.ctime()
        return filename

    def create_module(self,
                      filename,
                      really_compile=True,
                      standalone=False,
                      optimize=True,
                      exe_name=None):

        if standalone:
            return build_llvm_module.make_module_from_llvm(filename,
                                                           optimize=optimize,
                                                           exe_name=exe_name)
        else:
            postfix = ''
            basename = filename.purebasename + '_wrapper' + postfix + '.pyx'
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

def compile_module(function, annotation, view=False, **kwds):
    t = Translator(function)
    a = t.annotate(annotation)
    t.specialize()
    if view:
        t.view()
    return genllvm(t, **kwds)

def compile_function(function, annotation, **kwds):
    mod = compile_module(function, annotation, **kwds)
    return getattr(mod, 'pypy_' + function.func_name + "_wrapper")
