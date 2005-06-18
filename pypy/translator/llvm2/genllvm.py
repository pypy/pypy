from pypy.translator.llvm2 import build_llvm_module
from pypy.translator.llvm2.database import Database 
from pypy.translator.llvm2.pyxwrapper import write_pyx_wrapper 
from pypy.translator.llvm2.log import log 

from pypy.tool.udir import udir
from pypy.translator.llvm2.codewriter import CodeWriter

def genllvm(translator):
    func = translator.entrypoint

    db = Database(translator)
    entrynode = db.getnode(func)

    while db.process(): 
        pass

    codewriter = CodeWriter()
    dbobjects =  db.getobjects()
    for node in dbobjects:
        node.writedecl(codewriter) 
    for node in dbobjects:
        node.writeimpl(codewriter)
    
    targetdir = udir
    llvmsource = targetdir.join(func.func_name).new(ext='.ll')
    content = str(codewriter) 
    llvmsource.write(content) 
    log.source(content)
    
    pyxsource = llvmsource.new(basename=llvmsource.purebasename+'_wrapper'+'.pyx')
    write_pyx_wrapper(entrynode, pyxsource)    
    mod = build_llvm_module.make_module_from_llvm(llvmsource, pyxsource)
    return getattr(mod, func.func_name + "_wrapper")

