from pypy.translator.llvm2 import build_llvm_module
from pypy.translator.llvm2.funcgen import FunctionCodeGenerator
from pypy.tool.udir import udir
import py

def genllvm(translator):
    func = translator.entrypoint
    graph = translator.getflowgraph(func)
    targetdir = udir
    funcgen = FunctionCodeGenerator(graph, func)
    llvmfile = targetdir.join("f.ll")
    pyxfile = targetdir.join("f.pyx")
    f = llvmfile.open("w")
    print >> f, funcgen.declaration()
    print >> f, "{"
    for line in funcgen.implementation():
        print >> f, line
    print >> f, "}"
    f.close()
    f = pyxfile.open("w")
    py.test.skip("no pyrex wrapping support, check back tomorrow") 
    for line in funcgen.pyrex_wrapper():
        print >> f, line
    f.close()
    return build_llvm_module.make_module_from_llvm(llvmfile, pyxfile)
