from os.path import exists
use_boehm_gc = exists('/usr/lib/libgc.so') or exists('/usr/lib/libgc.a')

import py
from pypy.translator.llvm2 import build_llvm_module
from pypy.translator.llvm2.database import Database 
from pypy.translator.llvm2.pyxwrapper import write_pyx_wrapper 
from pypy.translator.llvm2.log import log
from pypy.objspace.flow.model import Constant
from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython import lltype
from pypy.tool.udir import udir
from pypy.translator.llvm2.codewriter import CodeWriter
from pypy.translator.llvm2.node import LLVMNode
from pypy.translator.backendoptimization import remove_void
#from pypy.translator.backendoptimization import rename_extfunc_calls
from pypy.translator.llvm2.extfunction import extdeclarations, \
     extfunctions, gc_boehm, gc_disabled, dependencies

from pypy.translator.translator import Translator

function_count = {}

class GenLLVM(object):

    def __init__(self, translator, embedexterns=True):
        self.db = Database(translator)
        self.translator = translator
        self.embedexterns = embedexterns
        # transformations
        remove_void(translator)
        #rename_extfunc_calls(translator)
        translator.checkgraphs()
        LLVMNode.used_external_functions = {}

    def compile(self, func=None):
        if func is None:
            func = self.translator.entrypoint
        self.entrypoint = func
        
        ptr = getfunctionptr(self.translator, func)
        c = inputconst(lltype.typeOf(ptr), ptr)
        self.db.prepare_repr_arg(c)
        assert c in self.db.obj2node
        self.db.setup_all()
        self.entrynode = self.db.obj2node[c]
        codewriter = CodeWriter()
        comment = codewriter.comment
        nl = codewriter.newline

        nl(); comment("Type Declarations"); nl()
        for typ_decl in self.db.getnodes():
            typ_decl.writedatatypedecl(codewriter)

        nl(); comment("Global Data") ; nl()
        for typ_decl in self.db.getnodes():
            typ_decl.writeglobalconstants(codewriter)

        nl(); comment("Function Prototypes") ; nl()
        if self.embedexterns:
            for extdecl in extdeclarations.split('\n'):
                codewriter.append(extdecl)
        for typ_decl in self.db.getnodes():
            typ_decl.writedecl(codewriter)

        #import pdb ; pdb.set_trace()
        nl(); comment("Function Implementation") 
        codewriter.startimpl()
        if use_boehm_gc:
            gc_funcs = gc_boehm
        else:
            gc_funcs = gc_disabled    
        for extfunc in gc_funcs.split('\n'):
            codewriter.append(extfunc)

        for typ_decl in self.db.getnodes():
            typ_decl.writeimpl(codewriter)

        depdone = {}
        for funcname,value in LLVMNode.used_external_functions.iteritems():
            deps = dependencies(funcname,[])
            deps.reverse()
            for dep in deps:
                if dep not in depdone:
                    llvm_code = extfunctions[dep][1]
                    for extfunc in llvm_code.split('\n'):
                        codewriter.append(extfunc)
                    depdone[dep] = True

        comment("End of file") ; nl()
        self.content = str(codewriter)
        return self.content

    def create_module(self):
        # hack to prevent running the same function twice in a test
        func = self.entrypoint
        if func.func_name in function_count:
            postfix = '_%d' % function_count[func.func_name]
            function_count[func.func_name] += 1
        else:
            postfix = ''
            function_count[func.func_name] = 1

        targetdir = udir
        llvmsource = targetdir.join(func.func_name+postfix).new(ext='.ll')
        llvmsource.write(self.content) 

        if not llvm_is_on_path(): 
            py.test.skip("llvm not found")  # XXX not good to call py.test.skip here

        pyxsource = llvmsource.new(basename=llvmsource.purebasename+'_wrapper'+postfix+'.pyx')
        write_pyx_wrapper(self.entrynode, pyxsource)    

        return build_llvm_module.make_module_from_llvm(llvmsource, pyxsource)
        
def genllvm(translator, embedexterns=True):
    gen = GenLLVM(translator, embedexterns=embedexterns)
    log.source(gen.compile())
    return gen.create_module()

def llvm_is_on_path():
    try:
        py.path.local.sysfind("llvm-as")
    except py.error.ENOENT: 
        return False 
    return True

def compile_module(function, annotate, view=False, embedexterns=True):
    t = Translator(function)
    a = t.annotate(annotate)
    t.specialize()
    a.simplify()
    if view:
        t.view()
    return genllvm(t, embedexterns=embedexterns)

def compile_function(function, annotate, view=False, embedexterns=True):
    mod = compile_module(function, annotate, view, embedexterns=embedexterns)
    return getattr(mod, function.func_name + "_wrapper")

def compile_module_function(function, annotate, view=False, embedexterns=True):
    mod = compile_module(function, annotate, view, embedexterns=embedexterns)
    f = getattr(mod, function.func_name + "_wrapper")
    return mod, f
