from pypy.rlib.parsing.tree import RPythonVisitor, Symbol
from pypy.lang.js import operations

class ASTBuilder(RPythonVisitor):
    BINOP_TO_CLS = {
        '+': operations.Plus,
        '-': operations.Minus,
        '*': operations.Mult,
        '/': operations.Div,
        '%': operations.Mod,
    }
    UNOP_TO_CLS = {
        '+': operations.UPlus,
        '-': operations.UMinus,
        '++': operations.Increment,
        '--': operations.Decrement,
    }
    LISTOP_TO_CLS = {
        '[': operations.Array,
        '{': operations.ObjectInit,
    }

    def get_instance(self, node, cls):
        value = ''
        source_pos = None
        if isinstance(node, Symbol):
            source_pos = node.token.source_pos
            value = node.additional_info
        else:
            curr = node.children[0]
            while not isinstance(curr, Symbol):
                if len(curr.children):
                    curr = curr.children[0]
                else:
                    source_pos = None
                    break
            else:
                source_pos = curr.token.source_pos

        # XXX some of the source positions are not perfect
        return cls(None,
                   value, 
                   source_pos.lineno,
                   source_pos.columnno,
                   source_pos.columnno + len(value))

    def visit_DECIMALLITERAL(self, node):
        result = self.get_instance(node, operations.Number)
        result.num = float(node.additional_info)
        return result

    def string(self,node):
        print node.additional_info
        result = self.get_instance(node, operations.String)
        result.strval = node.additional_info[1:-1] #XXX should do unquoting
        return result
    
    visit_DOUBLESTRING = string
    visit_SINGLESTRING = string

    def binaryop(self, node):
        left = self.dispatch(node.children[0])
        for i in range((len(node.children) - 1) // 2):
            op = node.children[i * 2 + 1]
            result = self.get_instance(
                    op, self.BINOP_TO_CLS[op.additional_info])
            right = self.dispatch(node.children[i * 2 + 2])
            result.left = left
            result.right = right
            left = result
        return left
    visit_additiveexpression = binaryop
    visit_multiplicativeexpression = binaryop

    def visit_unaryexpression(self, node):
        op = node.children[0]
        result = self.get_instance(
                op, self.UNOP_TO_CLS[op.additional_info])
        child = self.dispatch(node.children[1])
        result.expr = child
        result.postfix = False
        return result
    
    def listop(self, node):
        op = node.children[0]
        result = self.get_instance(
                op, self.LISTOP_TO_CLS[op.additional_info])
        l = [self.dispatch(child) for child in node.children[1:]]
        result.list = l
        return result
    visit_arrayliteral = listop
    visit_objectliteral = listop
    
    def visit_propertynameandvalue(self, node):
        result = self.get_instance(
                node, operations.PropertyInit)
        result.left = self.dispatch(node.children[0])
        result.right = self.dispatch(node.children[1])
        return result
    
    def visit_IDENTIFIERNAME(self, node):
        result = self.get_instance(node, operations.Identifier)
        result.name = node.additional_info
        result.initializer = operations.astundef #XXX this is uneded now
        print result
        return result
