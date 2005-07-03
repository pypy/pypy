


class ByteCode(object):
    def __init__(self, insn, node):
        self.insn = insn
        self.node = node
        
    def emit(self, ctx):
        """Emit bytecode given context"""
        ctx.set_lineno( node.lineno )
        ctx.emit( insn )

    def size(self):
        return 1


class LoadValue(ByteCode):
    def __init__(self, name, node):
        self.name = name
        self.node = node

    def emit(self, ctx):
        ctx.set_lineno( node.lineno )
        name_scope = ctx.get_name( self.name )
        if name_scope == "global":
            ctx.emit_arg('LOAD_GLOBAL', self.name )
        elif name_scope == "local":
            idx = ctx.get_local_idx( self.name )
            ctx.emit_arg('LOAD_FAST', idx )

class LoadConst(ByteCode):
    def __init__(self, cst, node ):
        self.cst = cst
        self.node = node

    def emit(self, ctx):
        ctx.set_lineno( node.lineno )
        ctx.emit_arg('LOAD_CONST', self.cst)

    def size(self):
        return 3

class CondJump(object):
    def __init__(self, cond, block ):
        self.nextBlock = block
        self.cond = cond # FWD, IF_TRUE, IF_FALSE, ABSOLUTE

    def emit(self, ctx):
        pass
