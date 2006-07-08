
def expr(src):
    from parser import source2ast
    module = source2ast(src)
    return module.node.nodes[0].expr

class AppTestFolder:
    def setup_class(cls):
        cls.w_expr, cls.w_check_const_fold = cls.space.unpackiterable(cls.space.appexec([], '''():
        from parser import source2ast, ASTConst, ASTNode
        from optimizers import Folder

        def expr(cls, src):
            module = source2ast(src)
            expr = module.node.nodes[0].expr
            assert isinstance(expr, cls)
            return expr

        def check_const_fold(src, value, cls=ASTNode):
            exprnode = expr(cls, src)
            exprnode = exprnode.mutate(Folder())
            assert isinstance(exprnode, ASTConst) and exprnode.value == value

        return expr, check_const_fold'''))

    def test_expr(self):
        from parser import ASTConst
        raises(AssertionError, self.expr, ASTConst, "a")

    def test_bitfold(self):
        from parser import ASTBitand, ASTBitor, ASTBitxor

        self.check_const_fold('1&3', 1, ASTBitand)
        self.check_const_fold('1|3', 3, ASTBitor)
        self.check_const_fold('1^3', 2, ASTBitxor)

        self.check_const_fold('1&3&5', 1, ASTBitand)
        self.check_const_fold('1|3|5', 7, ASTBitor)
        self.check_const_fold('1^3^5', 7, ASTBitxor)

    def test_binaryfold(self):
        from parser import ASTAdd, ASTSub, ASTMul, ASTDiv

        self.check_const_fold('1+3', 4, ASTAdd)
        self.check_const_fold('"1"+"3"', '13', ASTAdd)
        self.check_const_fold('1+3+6', 10, ASTAdd)

        self.check_const_fold('1+3-6', -2)

    def test_constant_tuples(self):
        from parser import ASTTuple

        self.check_const_fold('(1+1, 2)', (2, 2), ASTTuple)
        self.check_const_fold('((1,) + (1, 2),)', ((1, 1, 2),), ASTTuple)

        

