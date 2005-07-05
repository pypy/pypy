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
from pypy.translator.backendoptimization import remove_void

function_count = {}

def genllvm(translator):
    remove_void(translator)
    func = translator.entrypoint

    db = Database(translator)
    ptr = getfunctionptr(translator, func)
    c = inputconst(lltype.typeOf(ptr), ptr)
    db.prepare_repr_arg(c)
    assert c in db.obj2node
    db.setup_all()
    entrynode = db.obj2node[c]
    codewriter = CodeWriter()
    comment = codewriter.comment
    nl = codewriter.newline
    
    nl(); comment("Type Declarations"); nl()
    for typ_decl in db.getobjects():
        typ_decl.writedatatypedecl(codewriter)

    nl(); comment("Global Data") ; nl()
    for typ_decl in db.getobjects():
        typ_decl.writeglobalconstants(codewriter)

    nl(); comment("Function Prototypes") ; nl()
    if use_boehm_gc: 
        codewriter.declare('sbyte* %GC_malloc(uint)')
        codewriter.declare('sbyte* %GC_malloc_atomic(uint)')
        codewriter.declare('sbyte* %GC_realloc(sbyte*, uint)')
    for typ_decl in db.getobjects():
        typ_decl.writedecl(codewriter)

    #import pdb ; pdb.set_trace()
    nl(); comment("Function Implementation") 
    codewriter.startimpl()
    for typ_decl in db.getobjects():
        typ_decl.writeimpl(codewriter)

    comment("End of file") ; nl()

    if func.func_name in function_count:
        postfix = '_%d' % function_count[func.func_name]
        function_count[func.func_name] += 1
    else:
        postfix = ''
        function_count[func.func_name] = 1
    
    targetdir = udir
    llvmsource = targetdir.join(func.func_name+postfix).new(ext='.ll')
    content = str(codewriter) 
    llvmsource.write(content) 
    log.source(content)
  
    if not llvm_is_on_path(): 
        py.test.skip("llvm not found")  # XXX not good to call py.test.skip here

    pyxsource = llvmsource.new(basename=llvmsource.purebasename+'_wrapper'+postfix+'.pyx')
    write_pyx_wrapper(entrynode, pyxsource)    
    
    return build_llvm_module.make_module_from_llvm(llvmsource, pyxsource)

def llvm_is_on_path():
    try:
        py.path.local.sysfind("llvm-as")
    except py.error.ENOENT: 
        return False 
    return True
    
