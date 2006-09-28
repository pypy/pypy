from pypy.rpython.objectmodel import specialize


class GenVarOrConst(object):

    @specialize.arg(1)
    def revealconst(self, T):
        raise NotImplementedError

class GenVar(GenVarOrConst):
    is_const = False

class GenConst(GenVarOrConst):
    is_const = True


class CodeGenerator(object):
    pass

class CodeGenBlock(object):
    pass


class AbstractRGenOp(object):
    pass


class CodeGenSwitch(object):
    pass
