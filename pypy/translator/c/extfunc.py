import py
from pypy.rpython import extfunctable, lltype


class CHandWrittenWrapperFunctionCodeGenerator:

    def __init__(self, funcobj):
        self.funcobj = funcobj
        self.c_code = ll_externaltable[funcobj._callable]

    def argnames(self):
        argcount = len(lltype.typeOf(self.funcobj).ARGS)
        return ['a%d' % i for i in range(argcount)]

    def allconstantvalues(self):
        return []

    def cfunction_declarations(self):
        return []

    def cfunction_body(self):
        source = py.code.Source(self.c_code).strip()
        return list(source)


# map {ll_xyz_helper: bit of C code}

ll_externaltable = {

    extfunctable.ll_time_clock: """
        return ((double)clock()) / CLOCKS_PER_SEC;
    """,
}
