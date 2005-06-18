from pypy.translator.llvm2 import build_llvm_module
from pypy.translator.llvm2.funcgen import FunctionCodeGenerator
from pypy.tool.udir import udir
import py

def genllvm(translator):
    func = translator.entrypoint
    graph = translator.getflowgraph(func)
    targetdir = udir
    funcgen = FunctionCodeGenerator(graph, func)
    llvmsource = targetdir.join(func.func_name).new(ext='.ll')
    pyxsource = llvmsource.new(basename=llvmsource.purebasename+'_wrapper'+'.pyx')
    f = llvmsource.open("w")
    print >> f, funcgen.declaration()
    print >> f, "{"
    for line in funcgen.implementation():
        print >> f, line
    print >> f, "}"
    f.close()
    f = pyxsource.open("w")
    for line in funcgen.pyrex_wrapper():
        print >> f, line
    f.close()
    mod = build_llvm_module.make_module_from_llvm(llvmsource, pyxsource)
    return getattr(mod, func.func_name + "_wrapper")
