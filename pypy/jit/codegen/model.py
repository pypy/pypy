

class GenVarOrConst(object):
    pass

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
