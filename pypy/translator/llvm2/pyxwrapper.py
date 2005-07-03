from pypy.translator.llvm2.log import log 
from pypy.rpython import lltype 
log = log.pyrex 

PRIMITIVES_TO_C = {lltype.Signed: "int",
                   lltype.Unsigned: "unsigned int",
                   lltype.Bool: "char",
                   lltype.Float: "double",
                   lltype.Char: "char",
                   }

def write_pyx_wrapper(funcgen, targetpath): 
    def c_declaration():
        returntype = PRIMITIVES_TO_C[
            funcgen.graph.returnblock.inputargs[0].concretetype]
        inputargtypes = [PRIMITIVES_TO_C[arg.concretetype]
                             for arg in funcgen.graph.startblock.inputargs]
        result = "%s %s(%s)" % (returntype, funcgen.ref.lstrip("%"),
                                ", ".join(inputargtypes))
        return result
    lines = []
    append = lines.append
    inputargs = funcgen.db.repr_arg_multi(funcgen.graph.startblock.inputargs)
    inputargs = [x.strip("%") for x in inputargs]
    append("cdef extern " + c_declaration())
    append("")
    append("def %s_wrapper(%s):" % (funcgen.ref.strip("%"), ", ".join(inputargs)))
    append("    return %s(%s)" % (funcgen.ref.strip("%"), ", ".join(inputargs)))
    append("")
    targetpath.write("\n".join(lines))
  
