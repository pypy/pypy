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

def genllvm(translator):
    func = translator.entrypoint

    db = Database(translator)
    ptr = getfunctionptr(translator, func)
    c = inputconst(lltype.typeOf(ptr), ptr)
    db.prepare_repr_arg(c)
    assert c in db.obj2node
    while db.process(): 
        pass
    entrynode = db.obj2node[c]
    codewriter = CodeWriter()
    dbobjects =  db.getobjects()
    log.debug(dbobjects)
    log.debug(db.obj2node)
    for node in dbobjects:
        node.writedecl(codewriter) 
    codewriter.startimpl() 
    for node in dbobjects:
        node.writeimpl(codewriter)
    
    targetdir = udir
    llvmsource = targetdir.join(func.func_name).new(ext='.ll')
    content = str(codewriter) 
    llvmsource.write(content) 
    log.source(content)
  
    if not llvm_is_on_path(): 
        py.test.skip("llvm not found")  # XXX not good to call py.test.skip here
         
    pyxsource = llvmsource.new(basename=llvmsource.purebasename+'_wrapper'+'.pyx')
    write_pyx_wrapper(entrynode, pyxsource)    
    
    mod = build_llvm_module.make_module_from_llvm(llvmsource, pyxsource)
    return getattr(mod, func.func_name + "_wrapper")

def llvm_is_on_path():
    try:
        py.path.local.sysfind("llvm-as")
    except py.error.ENOENT: 
        return False 
    return True
    
