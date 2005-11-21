import sys
from pypy.translator.llvm.log import log 
from pypy.rpython.lltypesystem import lltype 
log = log.pyrex 

PRIMITIVES_TO_C = {lltype.Bool: "char",
                   lltype.Float: "double",
                   lltype.Char: "char",
                   }

# 32 bit platform
if sys.maxint == 2**31-1:
    PRIMITIVES_TO_C.update({
        lltype.Signed: "int",
        lltype.Unsigned: "unsigned int" })
    
# 64 bit platform
elif sys.maxint == 2**63-1:        
    PRIMITIVES_TO_C.update({
        lltype.Signed: "long",
        lltype.Unsigned: "unsigned long" })

else:
    assert False, "Unsupported platform"        

def write_pyx_wrapper(genllvm, targetpath): 
    funcgen = genllvm.entrynode
    def c_declaration():
        returntype = PRIMITIVES_TO_C[
            funcgen.graph.returnblock.inputargs[0].concretetype]
        inputargtypes = [PRIMITIVES_TO_C[arg.concretetype]
                             for arg in funcgen.graph.startblock.inputargs]
        result = "%s __entrypoint__%s(%s)" % (returntype, funcgen.ref.lstrip("%"),
                                ", ".join(inputargtypes))
        return result
    lines = []
    append = lines.append
    inputargs = funcgen.db.repr_arg_multi(funcgen.graph.startblock.inputargs)
    inputargs = [x.strip("%") for x in inputargs]
    append("cdef extern " + c_declaration())
    append("cdef extern int __entrypoint__raised_LLVMException()")
    append("cdef extern int Pyrex_RPython_StartupCode()")
    append("")
    append("setup = [False]")
    append("")
    append("class LLVMException(Exception):")
    append("    pass")
    append("")
    append(genllvm.gcpolicy.pyrex_code())
    append("def %s_wrapper(%s):" % (funcgen.ref.strip("%"), ", ".join(inputargs)))
    append("    if not setup[0]:")
    append("        startup = Pyrex_RPython_StartupCode()")
    append("        if not startup: raise Exception('Failure to startup')")
    append("        setup[0] = True")
    append("    result = __entrypoint__%s(%s)" % (funcgen.ref.strip("%"), ", ".join(inputargs)))
    append("    if __entrypoint__raised_LLVMException():    #not caught by the LLVM code itself")
    append("        raise LLVMException")
    append("    return result")
    append("")
    targetpath.write("\n".join(lines))
