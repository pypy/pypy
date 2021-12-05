import py
import os
from rpython.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from rpython.jit.tl.threadedcode.bytecode import *

currentdir = os.path.dirname(os.path.abspath(__file__))
grammar = py.path.local(currentdir).join('grammar.txt').read("rt")
regexs, rules, ToAST = parse_ebnf(grammar)
_parse = make_parse_function(regexs, rules, eof=True)

class Node(object):
    """ The abstract AST node
    """
    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self == other

class Program(Node):
    """ A list of expressions
    """
    def __init__(self, exprs):
        self.exprs = exprs

    def __repr__(self):
        return "Program({})".format(self.exprs)

    def compile(self, ctx):
        pass

class ConstInt(Node):
    def __init__(self, intval):
        self.intval = intval

    def __repr__(self):
        return "ConstInt({})".format(str(self.intval))

    def compile(self, ctx):
        pass

class ConstFloat(Node):
    def __init__(self, floatval):
        self.floatval = floatval

    def __repr__(self):
        return str(self.floatval)

    def compile(self, ctx):
        pass

class Variable(Node):
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return "Variable('{}')".format(self.val)

    def compile(self, ctx):
        pass

class BinOp(Node):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self):
        op, left, right = self.op, self.left, self.right
        return "BinOp('{}', {}, {})".format(op, left, right)

    def compile(self, ctx):
        pass

class Assignment(Node):
    def __init__(self, varname, expr):
        self.varname = varname
        self.expr = expr

    def __repr__(self):
        return "Assignment('{}', {})".format(
            self.varname, self.expr)

    def compile(self):
        pass

class Function(Node):
    def __init__(self, funcname, args, body):
        self.funcname = funcname
        self.args = args
        self.body = body

    def __repr__(self):
        return "Function('{}', {}, {})".format(
            self.funcname, self.args, self.body)


class FunApp(Node):
    def __init__(self, funcname, args):
        self.funcname = funcname
        self.args = args

    def __repr__(self):
        return "FunApp('{}', {})".format(
            self.funcname, self.args)


class Transformer(object):
    def _grab_exprs(self, star):
        exprs = []
        while len(star.children) == 2:
            exprs.append(self.visit_expr(star.children[0]))
            star = star.children[1]
        exprs.append(self.visit_expr(star.children[0]))
        return exprs

    def visit_main(self, node):
        exprs = self._grab_exprs(node.children[0])
        return Program(exprs)

    def visit_expr(self, node):
        if not hasattr(node.children[0], 'additional_info'):
            if len(node.children) == 1:
                return self.visit_simple_expr(node.children[0])
            else:
                name = self.visit_simple_expr(node.children[0])
                args = self.visit_actual_args(node.children[1])
                return FunApp(name, args)

        additional_info = node.children[0].additional_info
        if additional_info == 'let':
            return Assignment(node.children[1].additional_info,
                              self.visit_expr(node.children[3]))
        if additional_info == 'let rec':
            funcname = node.children[1].additional_info
            formal_args = self.visit_formal_args(node.children[2])
            body = self.visit_expr(node.children[4])
            return Function(funcname, formal_args, body)

        pass

    def visit_simple_expr(self, node):
        children = node.children
        chnode = children[0]
        if hasattr(chnode, 'additional_info'):
            if chnode.additional_info == '(':
                return self.visit_simple_expr(children[1])
        if len(children) == 1:
            return self.visit_atom(node.children[0])

        return BinOp(children[1].additional_info,
                     self.visit_atom(children[0]),
                     self.visit_simple_expr(children[2]))

    def visit_formal_args(self, node):
        args = []
        while True:
            args.append(node.children[0].additional_info)
            if len(node.children) == 1:
                break
            node = node.children[1]
        return args

    def visit_actual_args(self, node):
        args = []
        while True:
            args.append(self.visit_simple_expr(node.children[0]))
            if len(node.children) == 1:
                break
            node = node.children[1]
        return args

    def visit_atom(self, node):
        chnode = node.children[0]
        if chnode.symbol == 'DECIMAL':
            return ConstInt(int(chnode.additional_info))
        if chnode.symbol == 'VARIABLE':
            return Variable(chnode.additional_info)
        if chnode.symbol == 'FLOAT':
            return ConstFloat(float(chnode.additional_info))
        raise NotImplementedError

transformer = Transformer()

def parse(source):
    return transformer.visit_main(_parse(source))
