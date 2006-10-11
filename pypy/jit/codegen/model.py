from pypy.rpython.objectmodel import specialize


class NotConstant(Exception):
    pass


class GenVarOrConst(object):

    @specialize.arg(1)
    def revealconst(self, T):
        raise NotConstant(self)

class GenVar(GenVarOrConst):
    is_const = False

class GenConst(GenVarOrConst):
    is_const = True


class CodeGenerator(object):
    pass

class CodeGenBlock(object):
    pass


class AbstractRGenOp(object):

    # all commented out for the sake of the annotator
    pass

    #def newgraph(self, sigtoken):
    #    """ """
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.genconst(0)
    #def genconst(llvalue):
    #    """ """
    #    raise NotImplementedError

    #constPrebuiltGlobal = genconst

    #def gencallableconst(self, sigtoken, name, entrypointaddr):
    #    """ """
    #    raise NotImplementedError

    # the "token" methods render non-RPython data structures
    # (instances of LowLevelType) into RPython data structures.  they
    # are memo-specialized, so they can be full Python inside, but
    # each method must always return the same type, so the jit can
    # store the results in a list, for example (each backend can
    # decide what this type is independently, though)

    #@staticmethod
    #@specialize.memo()
    #def fieldToken(T, name):
    #    """ """
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def allocToken(T):
    #    """ """
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def varsizeAllocToken(T):
    #    """ """
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def arrayToken(A):
    #    """ """
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def kindToken(T):
    #    """ """
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def sigToken(FUNCTYPE):
    #    """ """
    #    raise NotImplementedError


class CodeGenSwitch(object):
    pass
