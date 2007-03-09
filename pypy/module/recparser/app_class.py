
# ______________________________________________________________________
# ParserError exception

class ParserError (Exception):
    """Class ParserError
    Exception class for parser errors (I assume).
    """

class ASTVisitor(object):
    """This is a visitor base class used to provide the visit
    method in replacement of the former visitor.visit = walker.dispatch
    It could also use to identify base type for visit arguments of AST nodes
    """

    def default(self, node):
        for child in node.getChildNodes():
            child.accept(self)
        return node

    def visitExpression(self, node):
        return self.default(node)
    def visitEmptyNode(self, node):
        return self.default(node)
    def visitAbstractFunction(self, node):
        return self.default( node )
    def visitAbstractTest(self, node):
        return self.default( node )
    def visitAdd(self, node):
        return self.default( node )
    def visitAnd(self, node):
        return self.default( node )
    def visitAssAttr(self, node):
        return self.default( node )
    def visitAssList(self, node):
        return self.default( node )
    def visitAssName(self, node):
        return self.default( node )
    def visitAssSeq(self, node):
        return self.default( node )
    def visitAssTuple(self, node):
        return self.default( node )
    def visitAssert(self, node):
        return self.default( node )
    def visitAssign(self, node):
        return self.default( node )
    def visitAugAssign(self, node):
        return self.default( node )
    def visitBackquote(self, node):
        return self.default( node )
    def visitBinaryOp(self, node):
        return self.default( node )
    def visitBitOp(self, node):
        return self.default( node )
    def visitBitand(self, node):
        return self.default( node )
    def visitBitor(self, node):
        return self.default( node )
    def visitBitxor(self, node):
        return self.default( node )
    def visitBreak(self, node):
        return self.default( node )
    def visitCallFunc(self, node):
        return self.default( node )
    def visitClass(self, node):
        return self.default( node )
    def visitCompare(self, node):
        return self.default( node )
    def visitCondExpr(self, node):
        return self.default( node )
    def visitConst(self, node):
        return self.default( node )
    def visitContinue(self, node):
        return self.default( node )
    def visitDecorators(self, node):
        return self.default( node )
    def visitDict(self, node):
        return self.default( node )
    def visitDiscard(self, node):
        return self.default( node )
    def visitDiv(self, node):
        return self.default( node )
    def visitEllipsis(self, node):
        return self.default( node )
    def visitExec(self, node):
        return self.default( node )
    def visitFloorDiv(self, node):
        return self.default( node )
    def visitFor(self, node):
        return self.default( node )
    def visitFrom(self, node):
        return self.default( node )
    def visitFunction(self, node):
        return self.default( node )
    def visitGenExpr(self, node):
        return self.default( node )
    def visitGenExprFor(self, node):
        return self.default( node )
    def visitGenExprIf(self, node):
        return self.default( node )
    def visitGenExprInner(self, node):
        return self.default( node )
    def visitGetattr(self, node):
        return self.default( node )
    def visitGlobal(self, node):
        return self.default( node )
    def visitIf(self, node):
        return self.default( node )
    def visitImport(self, node):
        return self.default( node )
    def visitInvert(self, node):
        return self.default( node )
    def visitKeyword(self, node):
        return self.default( node )
    def visitLambda(self, node):
        return self.default( node )
    def visitLeftShift(self, node):
        return self.default( node )
    def visitList(self, node):
        return self.default( node )
    def visitListComp(self, node):
        return self.default( node )
    def visitListCompFor(self, node):
        return self.default( node )
    def visitListCompIf(self, node):
        return self.default( node )
    def visitMod(self, node):
        return self.default( node )
    def visitModule(self, node):
        return self.default( node )
    def visitMul(self, node):
        return self.default( node )
    def visitName(self, node):
        return self.default( node )
    def visitNoneConst(self, node):
        return self.default( node )
    def visitNot(self, node):
        return self.default( node )
    def visitOr(self, node):
        return self.default( node )
    def visitPass(self, node):
        return self.default( node )
    def visitPower(self, node):
        return self.default( node )
    def visitPrint(self, node):
        return self.default( node )
    def visitPrintnl(self, node):
        return self.default( node )
    def visitRaise(self, node):
        return self.default( node )
    def visitReturn(self, node):
        return self.default( node )
    def visitRightShift(self, node):
        return self.default( node )
    def visitSlice(self, node):
        return self.default( node )
    def visitSliceobj(self, node):
        return self.default( node )
    def visitStmt(self, node):
        return self.default( node )
    def visitSub(self, node):
        return self.default( node )
    def visitSubscript(self, node):
        return self.default( node )
    def visitTryExcept(self, node):
        return self.default( node )
    def visitTryFinally(self, node):
        return self.default( node )
    def visitTuple(self, node):
        return self.default( node )
    def visitUnaryAdd(self, node):
        return self.default( node )
    def visitUnaryOp(self, node):
        return self.default( node )
    def visitUnarySub(self, node):
        return self.default( node )
    def visitWhile(self, node):
        return self.default( node )
    def visitWith(self, node):
        return self.default( node )
    def visitYield(self, node):
        return self.default( node )

class ASTMutator(ASTVisitor):
    """This class is similar to ASTVisitor, but will call
    node.mutate(self) instead of node.accept(self). The visitXXX
    methods of derived class should return the mutated node"""
    def default(self, node):
        return node

