import parser
class ConstMutator(parser.ASTMutator):
    def visitConst(self, node):
        if node.value == 3:
            node.value = 2
        return node

def threebecomestwo(ast, enc, filename):
    ast.mutate(ConstMutator())
    return ast

# install the hook
parser.install_compiler_hook(threebecomestwo)
print eval('3*2')
