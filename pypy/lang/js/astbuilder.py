from pypy.rlib.parsing.tree import RPythonVisitor, Symbol
from pypy.lang.js import operations

#this is a noop for now
def varfinder(opnode):
    return [] 
    if isinstance(opnode, operations.Vars):
        return [opnode,]
    elif hasattr(opnode, "nodes"):
        temp = []
        for op in opnode.nodes:
            temp.extend(varfinder(op))
        return temp
    elif hasattr(opnode, "body"):
        return varfinder(opnode.body)
    else:
        return []

#this is a noop for now
def funcfinder(opnode):
    return []
    if isinstance(opnode, operations.Function):
        return [opnode,]
    elif hasattr(opnode, "nodes"):
        return [funcfinder(op) for op in opnode.nodes]
    elif hasattr(opnode, "body"):
        return funcfinder(opnode.body)
    else:
        return []

class ASTBuilder(RPythonVisitor):
    BINOP_TO_CLS = {
        '+': operations.Plus,
        '-': operations.Minus,
        '*': operations.Mult,
        '/': operations.Division,
        '%': operations.Mod,
        '^': operations.BitwiseXor,
        '|': operations.BitwiseOr,
        '&': operations.BitwiseAnd,
        '&&': operations.And,
        '||': operations.Or,
        '==': operations.Eq,
        '!=': operations.Ne,
        '.': operations.Member,
        '[': operations.Member,
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
    
    def get_pos(self, node):
        value = ''
        source_pos = None
        if isinstance(node, Symbol):
            value = node.additional_info
            source_pos = node.token.source_pos
        else:
            curr = node.children[0]
            while not isinstance(curr, Symbol):
                if len(curr.children):
                    curr = curr.children[0]
                else:
                    break
            else:
                value = curr.additional_info
                source_pos = curr.token.source_pos

        # XXX some of the source positions are not perfect
        return operations.Position(
                   source_pos.lineno,
                   source_pos.columnno,
                   source_pos.columnno + len(value))

    def visit_DECIMALLITERAL(self, node):
        pos = self.get_pos(node)
        number = operations.Number(pos, float(node.additional_info))
        return number

    def string(self,node):
        pos = self.get_pos(node)
        return operations.String(pos, node.additional_info)
    visit_DOUBLESTRING = string
    visit_SINGLESTRING = string

    def binaryop(self, node):
        left = self.dispatch(node.children[0])
        for i in range((len(node.children) - 1) // 2):
            op = node.children[i * 2 + 1]
            pos = self.get_pos(op)
            right = self.dispatch(node.children[i * 2 + 2])
            result = self.BINOP_TO_CLS[op.additional_info](pos, left, right)
            print left, right
            left = result
        return left
    visit_additiveexpression = binaryop
    visit_multiplicativeexpression = binaryop
    visit_bitwisexorexpression = binaryop
    visit_bitwiseandexpression = binaryop
    visit_bitwiseorexpression = binaryop
    visit_equalityexpression = binaryop
    visit_logicalorexpression = binaryop
    visit_logicalandexpression = binaryop
    
    def visit_memberexpression(self, node):
        if isinstance(node.children[0], Symbol) and \
           node.children[0].additional_info == 'new': # XXX could be a identifier?
            # "new case"
            pos = self.get_pos(node)
            left = self.dispatch(node.children[1])
            right = self.dispatch(node.children[2])
            exp = operations.Call(pos, left, right)
            return operations.New(pos, exp)            
        else:
            return self.binaryop(node)


    def literalop(self, node):
        pos = self.get_pos(node);
        value = node.children[0].additional_info
        if value == "true":
            return operations.Boolean(pos, True)
        elif value == "false":
            return operations.Boolean(pos, False)
        else:
            return operations.Null(pos)
    visit_nullliteral = literalop
    visit_booleanliteral = literalop

    def visit_unaryexpression(self, node):
        op = node.children[0]
        pos = self.get_pos(op)
        child = self.dispatch(node.children[1])
        return self.UNOP_TO_CLS[op.additional_info](pos, child)
    
    def listop(self, node):
        op = node.children[0]
        pos = self.get_pos(op)
        l = [self.dispatch(child) for child in node.children[1:]]
        return self.LISTOP_TO_CLS[op.additional_info](pos, l)
    visit_arrayliteral = listop # XXX elision
    visit_objectliteral = listop
    
    def visit_propertynameandvalue(self, node):
        pos = self.get_pos(node)
        left = self.dispatch(node.children[0])
        right = self.dispatch(node.children[1])
        return operations.PropertyInit(pos,left,right)
    
    def visit_IDENTIFIERNAME(self, node):
        pos = self.get_pos(node)
        name = node.additional_info
        return operations.Identifier(pos, name)

    def visit_program(self, node):
        pos = self.get_pos(node)
        body = self.dispatch(node.children[0])
        return operations.Program(pos, body)
        
    def visit_sourceelements(self, node):
        pos = self.get_pos(node)
        nodes = [self.dispatch(child) for child in node.children]
        var_decl = []
        func_decl = []
        for node in nodes:
            var_decl.extend(varfinder(node))
            func_decl.extend(funcfinder(node))
        
        return operations.SourceElements(pos, var_decl, func_decl, nodes)
    
    def visit_expressionstatement(self, node):
        return self.dispatch(node.children[0])
    
    def visit_variablestatement(self, node):
        pos = self.get_pos(node)
        body = self.dispatch(node.children[0])
        return operations.Variable(pos, body)
    
    def visit_variabledeclarationlist(self, node):
        pos = self.get_pos(node)
        nodes = [self.dispatch(child) for child in node.children]
        return operations.VariableDeclList(pos, nodes)
    
    def visit_variabledeclaration(self, node):
        pos = self.get_pos(node)
        identifier = self.dispatch(node.children[0])
        if len(node.children) > 1:
            expr = self.dispatch(node.children[1])
        else:
            expr = None
        return operations.VariableDeclaration(pos, identifier, expr)
    
    def visit_callexpression(self, node):
        pos = self.get_pos(node)
        left = self.dispatch(node.children[0])
        right = self.dispatch(node.children[1])
        return operations.Call(pos, left, right)
    
    def visit_arguments(self, node):
        pos = self.get_pos(node)
        nodes = [self.dispatch(child) for child in node.children[1:]]
        return operations.ArgumentList(pos, nodes)
    
    def visit_assignmentexpression(self, node):
        pos = self.get_pos(node)
        left = self.dispatch(node.children[0])
        atype = node.children[1].additional_info
        right = self.dispatch(node.children[2])
        return operations.Assignment(pos, left, right, atype)
    
    def visit_functiondeclaration(self, node):
        pos = self.get_pos(node)
        
    def visit_throwstatement(self, node):
        pos = self.get_pos(node)
        exp = self.dispatch(node.children[0])
        return operations.Throw(pos, exp)
    
    def visit_emptystatement(self, node):
        return operations.astundef
    
    def visit_newexpression(self, node):
        if len(node.children) == 1:
            return self.dispatch(node.children[0])
        else:
            pos = self.get_pos(node)
            val = self.dispatch(node.children[0])
            return operations.New(pos, val)
    
