import parser, operator

def binaryVisit(operation):
    def visit(self, node):
        left = node.left
        right = node.right
        if isinstance(left, parser.ASTConst) and \
               isinstance(right, parser.ASTConst):
            if type(left.value) == type(right.value):
                return parser.ASTConst(operation(left.value, right.value))
        return node
    return visit

def bitopVisit(astclass, operation):
    def compress(values):
        while len(values) > 1:
            values[0] = operation(values[0], values[1])
            del values[1]
        return values[0]
    def visit(self, node):
        values = []
        for i, n in enumerate(node.nodes):
            if not isinstance(n, parser.ASTConst):
                if values:
                    return astclass([compress(values)] + node.nodes[i:])
                else:
                    return node
            values.append(n.value)
        return parser.ASTConst(compress(values))
    return visit
        

class Folder:
    def __init__(self):
        pass
        
    def defaultvisit(self, node):
        return node

    def __getattr__(self, attrname):
        if attrname.startswith('visit'):
            return self.defaultvisit
        raise AttributeError(attrname)

    visitAdd = binaryVisit(operator.add)
    visitSub = binaryVisit(operator.sub)
    visitMul = binaryVisit(operator.mul)
    visitDiv = binaryVisit(operator.div)

    visitBitand = bitopVisit(parser.ASTBitand, operator.and_)
    visitBitor  = bitopVisit(parser.ASTBitor, operator.or_)
    visitBitxor = bitopVisit(parser.ASTBitxor, operator.xor)

    def visitTuple(self, node):
        contents = []
        for n in node.nodes:
            if not isinstance(n, parser.ASTConst):
                return node
            contents.append(n.value)
        return parser.ASTConst(tuple(contents))

    def visitDiscard(self, node):
        if isinstance(node, parser.ASTConst):
            return None
        else:
            return node

def hook(ast, enc):
    return ast.mutate(Folder())
