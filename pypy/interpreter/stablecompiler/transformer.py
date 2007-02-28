"""Parse tree transformation module.

Transforms Python source code into an abstract syntax tree (AST)
defined in the ast module.

The simplest ways to invoke this module are via parse and parseFile.
parse(buf) -> AST
parseFile(path) -> AST
"""

# Original version written by Greg Stein (gstein@lyra.org)
#                         and Bill Tutt (rassilon@lima.mudlib.org)
# February 1997.
#
# Modifications and improvements for Python 2.0 by Jeremy Hylton and
# Mark Hammond
#
# Some fixes to try to have correct line number on almost all nodes
# (except Module, Discard and Stmt) added by Sylvain Thenault
#
# Portions of this file are:
# Copyright (C) 1997-1998 Greg Stein. All Rights Reserved.
#
# This module is provided under a BSD-ish license. See
#   http://www.opensource.org/licenses/bsd-license.html
# and replace OWNER, ORGANIZATION, and YEAR as appropriate.

# make sure we import the parser with the correct grammar
from pypy.interpreter.pyparser.pythonparse import make_pyparser

from pypy.interpreter.stablecompiler.ast import *
import parser
import pypy.interpreter.pyparser.pytoken as token
import sys

# Create parser from Grammar_stable, not current grammar.
# stable_grammar, _ = pythonparse.get_grammar_file("stable")
# stable_parser = pythonparse.python_grammar(stable_grammar)

stable_parser = make_pyparser('stable')

class symbol:
    pass
sym_name = {}
for name, value in stable_parser.symbols.items():
    sym_name[value] = name
    setattr(symbol, name, value)

# transforming is requiring a lot of recursion depth so make sure we have enough
if sys.getrecursionlimit()<2000:
    sys.setrecursionlimit(2000)


class WalkerError(StandardError):
    pass

from consts import CO_VARARGS, CO_VARKEYWORDS
from consts import OP_ASSIGN, OP_DELETE, OP_APPLY

   
def parseFile(path):
    f = open(path, "U")
    # XXX The parser API tolerates files without a trailing newline,
    # but not strings without a trailing newline.  Always add an extra
    # newline to the file contents, since we're going through the string
    # version of the API.
    src = f.read() + "\n"
    f.close()
    return parse(src)

# added a filename keyword argument to improve SyntaxErrors' messages
def parse(buf, mode="exec", filename=''):
    if mode == "exec" or mode == "single":
        return Transformer(filename).parsesuite(buf)
    elif mode == "eval":
        return Transformer(filename).parseexpr(buf)
    else:
        raise ValueError("compile() arg 3 must be"
                         " 'exec' or 'eval' or 'single'")

def asList(nodes):
    l = []
    for item in nodes:
        if hasattr(item, "asList"):
            l.append(item.asList())
        else:
            if type(item) is type( (None, None) ):
                l.append(tuple(asList(item)))
            elif type(item) is type( [] ):
                l.append(asList(item))
            else:
                l.append(item)
    return l

def extractLineNo(ast):
    if not isinstance(ast[1], tuple):
        # get a terminal node
        return ast[2]
    for child in ast[1:]:
        if isinstance(child, tuple):
            lineno = extractLineNo(child)
            if lineno is not None:
                return lineno

def Node(*args):
    kind = args[0]
    if nodes.has_key(kind):
        try:
            return nodes[kind](*args[1:])
        except TypeError:
            print nodes[kind], len(args), args
            raise
    else:
        raise WalkerError, "Can't find appropriate Node type: %s" % str(args)
        #return apply(ast.Node, args)

class Transformer:
    """Utility object for transforming Python parse trees.

    Exposes the following methods:
        tree = transform(ast_tree)
        tree = parsesuite(text)
        tree = parseexpr(text)
        tree = parsefile(fileob | filename)
    """

    def __init__(self, filename=''):
        self._dispatch = {}
        self.filename = filename
        for value, name in sym_name.items():
            if hasattr(self, name):
                self._dispatch[value] = getattr(self, name)
            
        self._dispatch[stable_parser.tokens['NEWLINE']] = self.com_NEWLINE
        self._atom_dispatch = {stable_parser.tokens['LPAR']: self.atom_lpar,
                               stable_parser.tokens['LSQB']: self.atom_lsqb,
                               stable_parser.tokens['LBRACE']: self.atom_lbrace,
                               stable_parser.tokens['BACKQUOTE']: self.atom_backquote,
                               stable_parser.tokens['NUMBER']: self.atom_number,
                               stable_parser.tokens['STRING']: self.atom_string,
                               stable_parser.tokens['NAME']: self.atom_name,
                               }
        self.encoding = None

    def syntaxerror(self, msg, node):
        offset = 0
        text = ""
        lineno = extractLineNo( node )
        args = ( self.filename, lineno, offset, text )
        raise SyntaxError( msg, args )

    def none_assignment_error(self, assigning, node):
        if assigning==OP_DELETE:
            self.syntaxerror( "deleting None", node )
        else:
            self.syntaxerror( "assignment to None", node )

    def transform(self, tree):
        """Transform an AST into a modified parse tree."""
        if not (isinstance(tree, tuple) or isinstance(tree, list)):
            tree = parser.ast2tuple(tree, line_info=1)
        return self.compile_node(tree)

    def parsesuite(self, text):
        """Return a modified parse tree for the given suite text."""
        return self.transform(parser.suite(text))

    def parseexpr(self, text):
        """Return a modified parse tree for the given expression text."""
        return self.transform(parser.expr(text))

    def parsefile(self, file):
        """Return a modified parse tree for the contents of the given file."""
        if type(file) == type(''):
            file = open(file)
        return self.parsesuite(file.read())

    # --------------------------------------------------------------
    #
    # PRIVATE METHODS
    #

    def compile_node(self, node):
        ### emit a line-number node?
        n = node[0]

        if n == symbol.encoding_decl:
            self.encoding = node[2]
            node = node[1]
            n = node[0]

        if n == symbol.single_input:
            return self.single_input(node[1:])
        if n == symbol.file_input:
            return self.file_input(node[1:])
        if n == symbol.eval_input:
            return self.eval_input(node[1:])
        if n == symbol.lambdef:
            return self.lambdef(node[1:])
        if n == symbol.funcdef:
            return self.funcdef(node[1:])
        if n == symbol.classdef:
            return self.classdef(node[1:])

        raise WalkerError, ('unexpected node type', n)

    def single_input(self, node):
        # NEWLINE | simple_stmt | compound_stmt NEWLINE
        n = node[0][0]
        if n != stable_parser.tokens['NEWLINE']:
            stmt = self.com_stmt(node[0])
        else:
            stmt = Pass()
        return Module(None, stmt)

    def file_input(self, nodelist):
        doc = self.get_docstring(nodelist, symbol.file_input)
        stmts = []
        for node in nodelist:
            if node[0] != stable_parser.tokens['ENDMARKER'] and node[0] != stable_parser.tokens['NEWLINE']:
                self.com_append_stmt(stmts, node)

        if doc is not None:
            assert isinstance(stmts[0], Discard)
            assert isinstance(stmts[0].expr, Const)
            del stmts[0]
        return Module(doc, Stmt(stmts))

    def eval_input(self, nodelist):
        # from the built-in function input()
        ### is this sufficient?
        return Expression(self.com_node(nodelist[0]))

    def decorator_name(self, nodelist):
        listlen = len(nodelist)
        assert listlen >= 1 and listlen % 2 == 1

        item = self.atom_name(nodelist)
        i = 1
        while i < listlen:
            assert nodelist[i][0] == stable_parser.tokens['DOT']
            assert nodelist[i + 1][0] == stable_parser.tokens['NAME']
            item = Getattr(item, nodelist[i + 1][1])
            i += 2

        return item

    def decorator(self, nodelist):
        # '@' dotted_name [ '(' [arglist] ')' ]
        assert len(nodelist) in (3, 5, 6)
        assert nodelist[0][0] == stable_parser.tokens['AT']
        assert nodelist[-1][0] == stable_parser.tokens['NEWLINE']

        assert nodelist[1][0] == symbol.dotted_name
        funcname = self.decorator_name(nodelist[1][1:])

        if len(nodelist) > 3:
            assert nodelist[2][0] == stable_parser.tokens['LPAR']
            expr = self.com_call_function(funcname, nodelist[3])
        else:
            expr = funcname

        return expr

    def decorators(self, nodelist):
        # decorators: decorator ([NEWLINE] decorator)* NEWLINE
        items = []
        for dec_nodelist in nodelist:
            assert dec_nodelist[0] == symbol.decorator
            items.append(self.decorator(dec_nodelist[1:]))
        return Decorators(items)

    def funcdef(self, nodelist):
        #                    -6   -5    -4         -3  -2    -1
        # funcdef: [decorators] 'def' NAME parameters ':' suite
        # parameters: '(' [varargslist] ')'

        if len(nodelist) == 6:
            assert nodelist[0][0] == symbol.decorators
            decorators = self.decorators(nodelist[0][1:])
        else:
            assert len(nodelist) == 5
            decorators = None

        lineno = nodelist[-4][2]
        name = nodelist[-4][1]
        args = nodelist[-3][2]

        if args[0] == symbol.varargslist:
            names, defaults, flags = self.com_arglist(args[1:])
        else:
            names = []
            defaults = []
            flags = 0
        doc = self.get_docstring(nodelist[-1])

        # code for function
        code = self.com_node(nodelist[-1])

        if doc is not None:
            assert isinstance(code, Stmt)
            assert isinstance(code.nodes[0], Discard)
            del code.nodes[0]
        if name == "None":
            self.none_assignment_error( OP_ASSIGN, nodelist[-4] )
        return Function(decorators, name, names, defaults, flags, doc, code,
                     lineno=lineno)

    def lambdef(self, nodelist):
        # lambdef: 'lambda' [varargslist] ':' test
        if nodelist[2][0] == symbol.varargslist:
            names, defaults, flags = self.com_arglist(nodelist[2][1:])
        else:
            names = []
            defaults = []
            flags = 0

        # code for lambda
        code = self.com_node(nodelist[-1])

        return Lambda(names, defaults, flags, code, lineno=nodelist[1][2])

    # (This is like lambdef but it uses the old_test instead.)
    # old_lambdef: 'lambda' [varargslist] ':' old_test
    old_lambdef = lambdef

    def classdef(self, nodelist):
        # classdef: 'class' NAME ['(' testlist ')'] ':' suite
        name = nodelist[1][1]
        doc = self.get_docstring(nodelist[-1])
        if nodelist[2][0] == stable_parser.tokens['COLON']:
            bases = []
        else:
            bases = self.com_bases(nodelist[3])

        # code for class
        code = self.com_node(nodelist[-1])

        if doc is not None:
            assert isinstance(code, Stmt)
            assert isinstance(code.nodes[0], Discard)
            del code.nodes[0]

        if name == "None":
            self.none_assignment_error(OP_ASSIGN, nodelist[1])
        return Class(name, bases, doc, code, lineno=nodelist[1][2])

    def stmt(self, nodelist):
        return self.com_stmt(nodelist[0])

    small_stmt = stmt
    flow_stmt = stmt
    compound_stmt = stmt

    def simple_stmt(self, nodelist):
        # small_stmt (';' small_stmt)* [';'] NEWLINE
        stmts = []
        for i in range(0, len(nodelist), 2):
            self.com_append_stmt(stmts, nodelist[i])
        return Stmt(stmts)

    def parameters(self, nodelist):
        raise WalkerError

    def varargslist(self, nodelist):
        raise WalkerError

    def fpdef(self, nodelist):
        raise WalkerError

    def fplist(self, nodelist):
        raise WalkerError

    def dotted_name(self, nodelist):
        raise WalkerError

    def comp_op(self, nodelist):
        raise WalkerError

    def trailer(self, nodelist):
        raise WalkerError

    def sliceop(self, nodelist):
        raise WalkerError

    def argument(self, nodelist):
        raise WalkerError

    # --------------------------------------------------------------
    #
    # STATEMENT NODES  (invoked by com_node())
    #

    def expr_stmt(self, nodelist):
        # augassign testlist | testlist ('=' testlist)*
        en = nodelist[-1]
        exprNode = self.lookup_node(en)(en[1:])
        if len(nodelist) == 1:
            return Discard(exprNode, lineno=exprNode.lineno)
        if nodelist[1][0] == stable_parser.tokens['EQUAL']:
            nodesl = []
            for i in range(0, len(nodelist) - 2, 2):
                nodesl.append(self.com_assign(nodelist[i], OP_ASSIGN))
            return Assign(nodesl, exprNode, lineno=nodelist[1][2])
        else:
            lval = self.com_augassign(nodelist[0])
            op = self.com_augassign_op(nodelist[1])
            return AugAssign(lval, op[1], exprNode, lineno=op[2])
        raise WalkerError, "can't get here"

    def print_stmt(self, nodelist):
        # print ([ test (',' test)* [','] ] | '>>' test [ (',' test)+ [','] ])
        items = []
        if len(nodelist) == 1:
            start = 1
            dest = None
        elif nodelist[1][0] == stable_parser.tokens['RIGHTSHIFT']:
            assert len(nodelist) == 3 \
                   or nodelist[3][0] == stable_parser.tokens['COMMA']
            dest = self.com_node(nodelist[2])
            start = 4
        else:
            dest = None
            start = 1
        for i in range(start, len(nodelist), 2):
            items.append(self.com_node(nodelist[i]))
        if nodelist[-1][0] == stable_parser.tokens['COMMA']:
            return Print(items, dest, lineno=nodelist[0][2])
        return Printnl(items, dest, lineno=nodelist[0][2])

    def del_stmt(self, nodelist):
        return self.com_assign(nodelist[1], OP_DELETE)

    def pass_stmt(self, nodelist):
        return Pass(lineno=nodelist[0][2])

    def break_stmt(self, nodelist):
        return Break(lineno=nodelist[0][2])

    def continue_stmt(self, nodelist):
        return Continue(lineno=nodelist[0][2])

    def return_stmt(self, nodelist):
        # return: [testlist]
        if len(nodelist) < 2:
            return Return(Const(None), lineno=nodelist[0][2])
        return Return(self.com_node(nodelist[1]), lineno=nodelist[0][2])

    def yield_stmt(self, nodelist):
        return Yield(self.com_node(nodelist[1]), lineno=nodelist[0][2])

    def raise_stmt(self, nodelist):
        # raise: [test [',' test [',' test]]]
        if len(nodelist) > 5:
            expr3 = self.com_node(nodelist[5])
        else:
            expr3 = None
        if len(nodelist) > 3:
            expr2 = self.com_node(nodelist[3])
        else:
            expr2 = None
        if len(nodelist) > 1:
            expr1 = self.com_node(nodelist[1])
        else:
            expr1 = None
        return Raise(expr1, expr2, expr3, lineno=nodelist[0][2])

    def import_stmt(self, nodelist):
        # import_stmt: import_name | import_from
        assert len(nodelist) == 1
        return self.com_node(nodelist[0])

    def import_name(self, nodelist):
        # import_name: 'import' dotted_as_names
        return Import(self.com_dotted_as_names(nodelist[1]),
                      lineno=nodelist[0][2])

    def import_from(self, nodelist):
        # import_from: 'from' dotted_name 'import' ('*' |
        #    '(' import_as_names ')' | import_as_names)
        assert nodelist[0][1] == 'from'
        assert nodelist[1][0] == symbol.dotted_name
        assert nodelist[2][1] == 'import'
        fromname = self.com_dotted_name(nodelist[1])
        if nodelist[3][0] == stable_parser.tokens['STAR']:
            return From(fromname, [('*', None)],
                        lineno=nodelist[0][2])
        else:
            if nodelist[3][0] == stable_parser.tokens['LPAR']:
                node = nodelist[4]
            else:
                node = nodelist[3]
                if node[-1][0] == stable_parser.tokens['COMMA']:
                    self.syntaxerror("trailing comma not allowed without surrounding parentheses", node)
            return From(fromname, self.com_import_as_names(node),
                        lineno=nodelist[0][2])

    def global_stmt(self, nodelist):
        # global: NAME (',' NAME)*
        names = []
        for i in range(1, len(nodelist), 2):
            names.append(nodelist[i][1])
        return Global(names, lineno=nodelist[0][2])

    def exec_stmt(self, nodelist):
        # exec_stmt: 'exec' expr ['in' expr [',' expr]]
        expr1 = self.com_node(nodelist[1])
        if len(nodelist) >= 4:
            expr2 = self.com_node(nodelist[3])
            if len(nodelist) >= 6:
                expr3 = self.com_node(nodelist[5])
            else:
                expr3 = None
        else:
            expr2 = expr3 = None

        return Exec(expr1, expr2, expr3, lineno=nodelist[0][2])

    def assert_stmt(self, nodelist):
        # 'assert': test, [',' test]
        expr1 = self.com_node(nodelist[1])
        if (len(nodelist) == 4):
            expr2 = self.com_node(nodelist[3])
        else:
            expr2 = None
        return Assert(expr1, expr2, lineno=nodelist[0][2])

    def if_stmt(self, nodelist):
        # if: test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
        tests = []
        for i in range(0, len(nodelist) - 3, 4):
            testNode = self.com_node(nodelist[i + 1])
            suiteNode = self.com_node(nodelist[i + 3])
            tests.append((testNode, suiteNode))

        if len(nodelist) % 4 == 3:
            elseNode = self.com_node(nodelist[-1])
##      elseNode.lineno = nodelist[-1][1][2]
        else:
            elseNode = None
        return If(tests, elseNode, lineno=nodelist[0][2])

    def while_stmt(self, nodelist):
        # 'while' test ':' suite ['else' ':' suite]

        testNode = self.com_node(nodelist[1])
        bodyNode = self.com_node(nodelist[3])

        if len(nodelist) > 4:
            elseNode = self.com_node(nodelist[6])
        else:
            elseNode = None

        return While(testNode, bodyNode, elseNode, lineno=nodelist[0][2])

    def for_stmt(self, nodelist):
        # 'for' exprlist 'in' exprlist ':' suite ['else' ':' suite]

        assignNode = self.com_assign(nodelist[1], OP_ASSIGN)
        listNode = self.com_node(nodelist[3])
        bodyNode = self.com_node(nodelist[5])

        if len(nodelist) > 8:
            elseNode = self.com_node(nodelist[8])
        else:
            elseNode = None

        return For(assignNode, listNode, bodyNode, elseNode,
                   lineno=nodelist[0][2])

    def try_stmt(self, nodelist):
        # 'try' ':' suite (except_clause ':' suite)+ ['else' ':' suite]
        # | 'try' ':' suite 'finally' ':' suite
        if nodelist[3][0] != symbol.except_clause:
            return self.com_try_finally(nodelist)

        return self.com_try_except(nodelist)

    def suite(self, nodelist):
        # simple_stmt | NEWLINE INDENT NEWLINE* (stmt NEWLINE*)+ DEDENT
        if len(nodelist) == 1:
            return self.com_stmt(nodelist[0])

        stmts = []
        for node in nodelist:
            if node[0] == symbol.stmt:
                self.com_append_stmt(stmts, node)
        return Stmt(stmts)

    # --------------------------------------------------------------
    #
    # EXPRESSION NODES  (invoked by com_node())
    #

    def testlist(self, nodelist):
        # testlist: expr (',' expr)* [',']
        # testlist_safe: old_test [(',' old_test)+ [',']]
        # exprlist: expr (',' expr)* [',']
        return self.com_binary(Tuple, nodelist)

    testlist_safe = testlist # XXX
    testlist1 = testlist
    exprlist = testlist

    def testlist_gexp(self, nodelist):
        if len(nodelist) == 2 and nodelist[1][0] == symbol.gen_for:
            test = self.com_node(nodelist[0])
            return self.com_generator_expression(test, nodelist[1])
        return self.testlist(nodelist)

    
    def test(self, nodelist):
        # test: or_test ['if' or_test 'else' test] | lambdef
        if len(nodelist) == 1:
            if nodelist[0][0] == symbol.lambdef:
                return self.lambdef(nodelist[0])
            else:
                # Normal or-expression
                return self.com_node(nodelist[0])
        elif len(nodelist) == 5 and nodelist[1][0] =='if':
            # Here we implement conditional expressions
            # XXX: CPython's nodename is IfExp, not CondExpr
            return CondExpr(delist[2], nodelist[0], nodelist[4],
                            nodelist[1].lineno)
        else:
            return self.com_binary(Or, nodelist)


    def and_test(self, nodelist):
        # not_test ('and' not_test)*
        return self.com_binary(And, nodelist)

    def old_test(self, nodelist):
        # old_test: or_test | old_lambdef
        if len(nodelist) == 1 and nodelist[0][0] == symbol.lambdef:
            return self.lambdef(nodelist[0])
        assert len(nodelist) == 1
        return self.com_node(nodelist[0])

    # XXX
    # test = old_test
    
    def or_test(self, nodelist):
        # or_test: and_test ('or' and_test)*
        return self.com_binary(Or, nodelist)

    def not_test(self, nodelist):
        # 'not' not_test | comparison
        result = self.com_node(nodelist[-1])
        if len(nodelist) == 2:
            return Not(result, lineno=nodelist[0][2])
        return result

    def comparison(self, nodelist):
        # comparison: expr (comp_op expr)*
        node = self.com_node(nodelist[0])
        if len(nodelist) == 1:
            return node

        results = []
        for i in range(2, len(nodelist), 2):
            nl = nodelist[i-1]

            # comp_op: '<' | '>' | '=' | '>=' | '<=' | '<>' | '!=' | '=='
            #          | 'in' | 'not' 'in' | 'is' | 'is' 'not'
            n = nl[1]
            if n[0] == stable_parser.tokens['NAME']:
                type = n[1]
                if len(nl) == 3:
                    if type == 'not':
                        type = 'not in'
                    else:
                        type = 'is not'
            else:
                type = _cmp_types[n[0]]

            lineno = nl[1][2]
            results.append((type, self.com_node(nodelist[i])))

        # we need a special "compare" node so that we can distinguish
        #   3 < x < 5   from    (3 < x) < 5
        # the two have very different semantics and results (note that the
        # latter form is always true)

        return Compare(node, results, lineno=lineno)

    def expr(self, nodelist):
        # xor_expr ('|' xor_expr)*
        return self.com_binary(Bitor, nodelist)

    def xor_expr(self, nodelist):
        # xor_expr ('^' xor_expr)*
        return self.com_binary(Bitxor, nodelist)

    def and_expr(self, nodelist):
        # xor_expr ('&' xor_expr)*
        return self.com_binary(Bitand, nodelist)

    def shift_expr(self, nodelist):
        # shift_expr ('<<'|'>>' shift_expr)*
        node = self.com_node(nodelist[0])
        for i in range(2, len(nodelist), 2):
            right = self.com_node(nodelist[i])
            if nodelist[i-1][0] == stable_parser.tokens['LEFTSHIFT']:
                node = LeftShift([node, right], lineno=nodelist[1][2])
            elif nodelist[i-1][0] == stable_parser.tokens['RIGHTSHIFT']:
                node = RightShift([node, right], lineno=nodelist[1][2])
            else:
                raise ValueError, "unexpected token: %s" % nodelist[i-1][0]
        return node

    def arith_expr(self, nodelist):
        node = self.com_node(nodelist[0])
        for i in range(2, len(nodelist), 2):
            right = self.com_node(nodelist[i])
            if nodelist[i-1][0] == stable_parser.tokens['PLUS']:
                node = Add([node, right], lineno=nodelist[1][2])
            elif nodelist[i-1][0] == stable_parser.tokens['MINUS']:
                node = Sub([node, right], lineno=nodelist[1][2])
            else:
                raise ValueError, "unexpected token: %s" % nodelist[i-1][0]
        return node

    def term(self, nodelist):
        node = self.com_node(nodelist[0])
        for i in range(2, len(nodelist), 2):
            right = self.com_node(nodelist[i])
            t = nodelist[i-1][0]
            if t == stable_parser.tokens['STAR']:
                node = Mul([node, right])
            elif t == stable_parser.tokens['SLASH']:
                node = Div([node, right])
            elif t == stable_parser.tokens['PERCENT']:
                node = Mod([node, right])
            elif t == stable_parser.tokens['DOUBLESLASH']:
                node = FloorDiv([node, right])
            else:
                raise ValueError, "unexpected token: %s" % t
            node.lineno = nodelist[1][2]
        return node

    def factor(self, nodelist):
        elt = nodelist[0]
        t = elt[0]
        node = self.lookup_node(nodelist[-1])(nodelist[-1][1:])
        # need to handle (unary op)constant here...
        if t == stable_parser.tokens['PLUS']:
            return UnaryAdd(node, lineno=elt[2])
        elif t == stable_parser.tokens['MINUS']:
            return UnarySub(node, lineno=elt[2])
        elif t == stable_parser.tokens['TILDE']:
            node = Invert(node, lineno=elt[2])
        return node

    def power(self, nodelist):
        # power: atom trailer* ('**' factor)*
        node = self.com_node(nodelist[0])
        for i in range(1, len(nodelist)):
            elt = nodelist[i]
            if elt[0] == stable_parser.tokens['DOUBLESTAR']:
                return Power([node, self.com_node(nodelist[i+1])],
                             lineno=elt[2])

            node = self.com_apply_trailer(node, elt)

        return node

    def atom(self, nodelist):
        return self._atom_dispatch[nodelist[0][0]](nodelist)
        n.lineno = nodelist[0][2]
        return n

    def atom_lpar(self, nodelist):
        if nodelist[1][0] == stable_parser.tokens['RPAR']:
            return Tuple(())
        return self.com_node(nodelist[1])

    def atom_lsqb(self, nodelist):
        if nodelist[1][0] == stable_parser.tokens['RSQB']:
            return List([], lineno=nodelist[0][2])
        return self.com_list_constructor(nodelist[1], nodelist[0][2])

    def atom_lbrace(self, nodelist):
        if nodelist[1][0] == stable_parser.tokens['RBRACE']:
            return Dict(())
        return self.com_dictmaker(nodelist[1])

    def atom_backquote(self, nodelist):
        return Backquote(self.com_node(nodelist[1]))

    def atom_number(self, nodelist):
        ### need to verify this matches compile.c
        k = eval(nodelist[0][1])
        return Const(k, lineno=nodelist[0][2])

    def decode_literal(self, lit):
        if self.encoding:
            # this is particularly fragile & a bit of a
            # hack... changes in compile.c:parsestr and
            # tokenizer.c must be reflected here.
            if self.encoding not in ['utf-8', 'iso-8859-1']:
                lit = unicode(lit, 'utf-8').encode(self.encoding)
            return eval("# coding: %s\n%s" % (self.encoding, lit))
        else:
            return eval(lit)

    def atom_string(self, nodelist):
        k = ''
        for node in nodelist:
            k += self.decode_literal(node[1])
        return Const(k, lineno=nodelist[0][2])

    def atom_name(self, nodelist):
        return Name(nodelist[0][1], lineno=nodelist[0][2])

    # --------------------------------------------------------------
    #
    # INTERNAL PARSING UTILITIES
    #

    # The use of com_node() introduces a lot of extra stack frames,
    # enough to cause a stack overflow compiling test.test_parser with
    # the standard interpreter recursionlimit.  The com_node() is a
    # convenience function that hides the dispatch details, but comes
    # at a very high cost.  It is more efficient to dispatch directly
    # in the callers.  In these cases, use lookup_node() and call the
    # dispatched node directly.

    def lookup_node(self, node):
        return self._dispatch[node[0]]

    _callers = {}

    def com_node(self, node):
        # Note: compile.c has handling in com_node for del_stmt, pass_stmt,
        #       break_stmt, stmt, small_stmt, flow_stmt, simple_stmt,
        #       and compound_stmt.
        #       We'll just dispatch them.
        return self._dispatch[node[0]](node[1:])

    def com_NEWLINE(self, *args):
        # A ';' at the end of a line can make a NEWLINE token appear
        # here, Render it harmless. (genc discards ('discard',
        # ('const', xxxx)) Nodes)
        return Discard(Const(None))

    def com_arglist(self, nodelist):
        # varargslist:
        #     (fpdef ['=' test] ',')* ('*' NAME [',' '**' NAME] | '**' NAME)
        #   | fpdef ['=' test] (',' fpdef ['=' test])* [',']
        # fpdef: NAME | '(' fplist ')'
        # fplist: fpdef (',' fpdef)* [',']
        names = []
        defaults = []
        flags = 0
        i = 0
        while i < len(nodelist):
            node = nodelist[i]
            if node[0] == stable_parser.tokens['STAR'] or node[0] == stable_parser.tokens['DOUBLESTAR']:
                if node[0] == stable_parser.tokens['STAR']:
                    node = nodelist[i+1]
                    if node[0] == stable_parser.tokens['NAME']:
                        name = node[1]
                        if name in names:
                            self.syntaxerror("duplicate argument '%s' in function definition" %
                                             name, node)
                        names.append(name)
                        flags = flags | CO_VARARGS
                        i = i + 3

                if i < len(nodelist):
                    # should be DOUBLESTAR
                    t = nodelist[i][0]
                    if t == stable_parser.tokens['DOUBLESTAR']:
                        node = nodelist[i+1]
                    else:
                        raise ValueError, "unexpected token: %s" % t
                    name = node[1]
                    if name in names:
                        self.syntaxerror("duplicate argument '%s' in function definition" %
                                         name, node)
                    names.append(name)
                    flags = flags | CO_VARKEYWORDS

                break

            # fpdef: NAME | '(' fplist ')'
            name = self.com_fpdef(node)
            if name in names:
                self.syntaxerror("duplicate argument '%s' in function definition" %
                                         name, node)
            names.append(name)

            i = i + 1
            if i >= len(nodelist):
                if len(defaults):
                    self.syntaxerror("non-default argument follows default argument",node)
                break
            
            if nodelist[i][0] == stable_parser.tokens['EQUAL']:
                defaults.append(self.com_node(nodelist[i + 1]))
                i = i + 2
            elif len(defaults):
                self.syntaxerror("non-default argument follows default argument",node)

            i = i + 1

        if "None" in names:
            self.syntaxerror( "Invalid syntax.  Assignment to None.", node)
        return names, defaults, flags

    def com_fpdef(self, node):
        # fpdef: NAME | '(' fplist ')'
        if node[1][0] == stable_parser.tokens['LPAR']:
            return self.com_fplist(node[2])
        return node[1][1]

    def com_fplist(self, node):
        # fplist: fpdef (',' fpdef)* [',']
        if len(node) == 2:
            return self.com_fpdef(node[1])
        list = []
        for i in range(1, len(node), 2):
            list.append(self.com_fpdef(node[i]))
        return tuple(list)

    def com_dotted_name(self, node):
        # String together the dotted names and return the string
        name = ""
        for n in node:
            if type(n) == type(()) and n[0] == stable_parser.tokens['NAME']:
                name = name + n[1] + '.'
        return name[:-1]

    def com_dotted_as_name(self, node):
        assert node[0] == symbol.dotted_as_name
        node = node[1:]
        dot = self.com_dotted_name(node[0][1:])
        if len(node) == 1:
            return dot, None
        assert node[1][1] == 'as'
        assert node[2][0] == stable_parser.tokens['NAME']
        return dot, node[2][1]

    def com_dotted_as_names(self, node):
        assert node[0] == symbol.dotted_as_names
        node = node[1:]
        names = [self.com_dotted_as_name(node[0])]
        for i in range(2, len(node), 2):
            names.append(self.com_dotted_as_name(node[i]))
        return names

    def com_import_as_name(self, node):
        assert node[0] == symbol.import_as_name
        node = node[1:]
        assert node[0][0] == stable_parser.tokens['NAME']
        if len(node) == 1:
            return node[0][1], None
        assert node[1][1] == 'as', node
        assert node[2][0] == stable_parser.tokens['NAME']
        return node[0][1], node[2][1]

    def com_import_as_names(self, node):
        assert node[0] == symbol.import_as_names
        node = node[1:]
        names = [self.com_import_as_name(node[0])]
        for i in range(2, len(node), 2):
            names.append(self.com_import_as_name(node[i]))
        return names

    def com_bases(self, node):
        bases = []
        for i in range(1, len(node), 2):
            bases.append(self.com_node(node[i]))
        return bases

    def com_try_finally(self, nodelist):
        # try_fin_stmt: "try" ":" suite "finally" ":" suite
        return TryFinally(self.com_node(nodelist[2]),
                       self.com_node(nodelist[5]),
                       lineno=nodelist[0][2])

    def com_try_except(self, nodelist):
        # try_except: 'try' ':' suite (except_clause ':' suite)* ['else' suite]
        #tryexcept:  [TryNode, [except_clauses], elseNode)]
        stmt = self.com_node(nodelist[2])
        clauses = []
        elseNode = None
        for i in range(3, len(nodelist), 3):
            node = nodelist[i]
            if node[0] == symbol.except_clause:
                # except_clause: 'except' [expr [',' expr]] */
                if len(node) > 2:
                    expr1 = self.com_node(node[2])
                    if len(node) > 4:
                        expr2 = self.com_assign(node[4], OP_ASSIGN)
                    else:
                        expr2 = None
                else:
                    expr1 = expr2 = None
                clauses.append((expr1, expr2, self.com_node(nodelist[i+2])))

            if node[0] == stable_parser.tokens['NAME']:
                elseNode = self.com_node(nodelist[i+2])
        return TryExcept(self.com_node(nodelist[2]), clauses, elseNode,
                         lineno=nodelist[0][2])

    def com_augassign_op(self, node):
        assert node[0] == symbol.augassign
        return node[1]

    def com_augassign(self, node):
        """Return node suitable for lvalue of augmented assignment

        Names, slices, and attributes are the only allowable nodes.
        """
        l = self.com_node(node)
        if isinstance(l, Name):
            if l.name == "__debug__":
                self.syntaxerror( "can not assign to __debug__", node )
            if l.name == "None":
                self.none_assignment_error( OP_ASSIGN, node )
        if l.__class__ in (Name, Slice, Subscript, Getattr):
            return l
        self.syntaxerror( "can't assign to %s" % l.__class__.__name__, node)

    def com_assign(self, node, assigning):
        # return a node suitable for use as an "lvalue"
        # loop to avoid trivial recursion
        while 1:
            t = node[0]
            if t == symbol.exprlist or t == symbol.testlist or t == symbol.testlist_gexp:
                if len(node) > 2:
                    return self.com_assign_tuple(node, assigning)
                node = node[1]
            elif t in _assign_types:
                if len(node) > 2:
                    self.syntaxerror( "can't assign to operator", node)
                node = node[1]
            elif t == symbol.power:
                if node[1][0] != symbol.atom:
                    self.syntaxerror( "can't assign to operator", node)
                if len(node) > 2:
                    primary = self.com_node(node[1])
                    for i in range(2, len(node)-1):
                        ch = node[i]
                        if ch[0] == stable_parser.tokens['DOUBLESTAR']:
                            self.syntaxerror( "can't assign to operator", node)
                        primary = self.com_apply_trailer(primary, ch)
                    return self.com_assign_trailer(primary, node[-1],
                                                   assigning)
                node = node[1]
            elif t == symbol.atom:
                t = node[1][0]
                if t == stable_parser.tokens['LPAR']:
                    node = node[2]
                    if node[0] == stable_parser.tokens['RPAR']:
                        self.syntaxerror( "can't assign to ()", node)
                elif t == stable_parser.tokens['LSQB']:
                    node = node[2]
                    if node[0] == stable_parser.tokens['RSQB']:
                        self.syntaxerror( "can't assign to []", node)
                    return self.com_assign_list(node, assigning)
                elif t == stable_parser.tokens['NAME']:
                    if node[1][1] == "__debug__":
                        self.syntaxerror( "can not assign to __debug__", node )
                    if node[1][1] == "None":
                        self.none_assignment_error(assigning, node)
                    return self.com_assign_name(node[1], assigning)
                else:
                    self.syntaxerror( "can't assign to literal", node)
            else:
                self.syntaxerror( "bad assignment", node)

    def com_assign_tuple(self, node, assigning):
        assigns = []
        if len(node)>=3:
            if node[2][0] == symbol.gen_for:
                self.syntaxerror("assign to generator expression not possible", node)
        for i in range(1, len(node), 2):
            assigns.append(self.com_assign(node[i], assigning))
        return AssTuple(assigns, lineno=extractLineNo(node))

    def com_assign_list(self, node, assigning):
        assigns = []
        for i in range(1, len(node), 2):
            if i + 1 < len(node):
                if node[i + 1][0] == symbol.list_for:
                    self.syntaxerror( "can't assign to list comprehension", node)
                assert node[i + 1][0] == stable_parser.tokens['COMMA'], node[i + 1]
            assigns.append(self.com_assign(node[i], assigning))
        return AssList(assigns, lineno=extractLineNo(node))

    def com_assign_name(self, node, assigning):
        return AssName(node[1], assigning, lineno=node[2])

    def com_assign_trailer(self, primary, node, assigning):
        t = node[1][0]
        if t == stable_parser.tokens['DOT']:
            return self.com_assign_attr(primary, node[2], assigning)
        if t == stable_parser.tokens['LSQB']:
            return self.com_subscriptlist(primary, node[2], assigning)
        if t == stable_parser.tokens['LPAR']:
            if assigning==OP_DELETE:
                self.syntaxerror( "can't delete function call", node)
            else:
                self.syntaxerror( "can't assign to function call", node)
        self.syntaxerror( "unknown trailer type: %s" % t, node)

    def com_assign_attr(self, primary, node, assigning):
        if node[1]=="None":
            self.none_assignment_error(assigning, node)
        return AssAttr(primary, node[1], assigning, lineno=node[-1])

    def com_binary(self, constructor, nodelist):
        "Compile 'NODE (OP NODE)*' into (type, [ node1, ..., nodeN ])."
        l = len(nodelist)
        if l == 1:
            n = nodelist[0]
            return self.lookup_node(n)(n[1:])
        items = []
        for i in range(0, l, 2):
            n = nodelist[i]
            items.append(self.lookup_node(n)(n[1:]))
        return constructor(items, lineno=extractLineNo(nodelist))

    def com_stmt(self, node):
        result = self.lookup_node(node)(node[1:])
        assert result is not None
        if isinstance(result, Stmt):
            return result
        return Stmt([result])

    def com_append_stmt(self, stmts, node):
        result = self.lookup_node(node)(node[1:])
        assert result is not None
        if isinstance(result, Stmt):
            stmts.extend(result.nodes)
        else:
            stmts.append(result)

    if hasattr(symbol, 'list_for'):
        def com_list_constructor(self, nodelist, lineno):
            # listmaker: test ( list_for | (',' test)* [','] )
            values = []
            for i in range(1, len(nodelist)):
                if nodelist[i][0] == symbol.list_for:
                    assert len(nodelist[i:]) == 1
                    return self.com_list_comprehension(values[0],
                                                       nodelist[i])
                elif nodelist[i][0] == stable_parser.tokens['COMMA']:
                    continue
                values.append(self.com_node(nodelist[i]))
            return List(values, lineno=lineno)

        def com_list_comprehension(self, expr, node):
            # list_iter: list_for | list_if
            # list_for: 'for' exprlist 'in' testlist [list_iter]
            # list_if: 'if' test [list_iter]

            # XXX should raise SyntaxError for assignment

            lineno = node[1][2]
            fors = []
            while node:
                t = node[1][1]
                if t == 'for':
                    assignNode = self.com_assign(node[2], OP_ASSIGN)
                    listNode = self.com_node(node[4])
                    newfor = ListCompFor(assignNode, listNode, [])
                    newfor.lineno = node[1][2]
                    fors.append(newfor)
                    if len(node) == 5:
                        node = None
                    else:
                        node = self.com_list_iter(node[5])
                elif t == 'if':
                    test = self.com_node(node[2])
                    newif = ListCompIf(test, lineno=node[1][2])
                    newfor.ifs.append(newif)
                    if len(node) == 3:
                        node = None
                    else:
                        node = self.com_list_iter(node[3])
                else:
                    self.syntaxerror(
                        "unexpected list comprehension element: %s %d"
                        % (node, lineno), node)
            return ListComp(expr, fors, lineno=lineno)

        def com_list_iter(self, node):
            assert node[0] == symbol.list_iter
            return node[1]
    else:
        def com_list_constructor(self, nodelist, lineno):
            values = []
            for i in range(1, len(nodelist), 2):
                values.append(self.com_node(nodelist[i]))
            return List(values, lineno)

    if hasattr(symbol, 'gen_for'):
        def com_generator_expression(self, expr, node):
            # gen_iter: gen_for | gen_if
            # gen_for: 'for' exprlist 'in' test [gen_iter]
            # gen_if: 'if' test [gen_iter]

            lineno = node[1][2]
            fors = []
            while node:
                t = node[1][1]
                if t == 'for':
                    assignNode = self.com_assign(node[2], OP_ASSIGN)
                    genNode = self.com_node(node[4])
                    newfor = GenExprFor(assignNode, genNode, [],
                                        lineno=node[1][2])
                    fors.append(newfor)
                    if (len(node)) == 5:
                        node = None
                    else:
                        node = self.com_gen_iter(node[5])
                elif t == 'if':
                    test = self.com_node(node[2])
                    newif = GenExprIf(test, lineno=node[1][2])
                    newfor.ifs.append(newif)
                    if len(node) == 3:
                        node = None
                    else:
                        node = self.com_gen_iter(node[3])
                else:
                    self.syntaxerror(
                        "unexpected generator expression element: %s %d"
                        % (node, lineno), node)
            fors[0].is_outmost = True
            return GenExpr(GenExprInner(expr, fors), lineno=lineno)

        def com_gen_iter(self, node):
            assert node[0] == symbol.gen_iter
            return node[1]

    def com_dictmaker(self, nodelist):
        # dictmaker: test ':' test (',' test ':' value)* [',']
        items = []
        for i in range(1, len(nodelist), 4):
            items.append((self.com_node(nodelist[i]),
                          self.com_node(nodelist[i+2])))
        return Dict(items)

    def com_apply_trailer(self, primaryNode, nodelist):
        t = nodelist[1][0]
        if t == stable_parser.tokens['LPAR']:
            return self.com_call_function(primaryNode, nodelist[2])
        if t == stable_parser.tokens['DOT']:
            return self.com_select_member(primaryNode, nodelist[2])
        if t == stable_parser.tokens['LSQB']:
            return self.com_subscriptlist(primaryNode, nodelist[2], OP_APPLY)

        self.syntaxerror( 'unknown node type: %s' % t, nodelist[1])

    def com_select_member(self, primaryNode, nodelist):
        if nodelist[0] != stable_parser.tokens['NAME']:
            self.syntaxerror( "member must be a name", nodelist[0])
        return Getattr(primaryNode, nodelist[1], lineno=nodelist[2])

    def com_call_function(self, primaryNode, nodelist):
        if nodelist[0] == stable_parser.tokens['RPAR']:
            return CallFunc(primaryNode, [], lineno=extractLineNo(nodelist))
        args = []
        kw = 0
        len_nodelist = len(nodelist)
        for i in range(1, len_nodelist, 2):
            node = nodelist[i]
            if node[0] == stable_parser.tokens['STAR'] or node[0] == stable_parser.tokens['DOUBLESTAR']:
                break
            kw, result = self.com_argument(node, kw)

            if len_nodelist != 2 and isinstance(result, GenExpr) \
               and len(node) == 3 and node[2][0] == symbol.gen_for:
                # allow f(x for x in y), but reject f(x for x in y, 1)
                # should use f((x for x in y), 1) instead of f(x for x in y, 1)
                self.syntaxerror( 'generator expression needs parenthesis', node)

            args.append(result)
        else:
            # No broken by star arg, so skip the last one we processed.
            i = i + 1
        if i < len_nodelist and nodelist[i][0] == stable_parser.tokens['COMMA']:
            # need to accept an application that looks like "f(a, b,)"
            i = i + 1
        star_node = dstar_node = None
        while i < len_nodelist:
            tok = nodelist[i]
            ch = nodelist[i+1]
            i = i + 3
            if tok[0]==stable_parser.tokens['STAR']:
                if star_node is not None:
                    self.syntaxerror( 'already have the varargs indentifier', tok )
                star_node = self.com_node(ch)
            elif tok[0]==stable_parser.tokens['DOUBLESTAR']:
                if dstar_node is not None:
                    self.syntaxerror( 'already have the kwargs indentifier', tok )
                dstar_node = self.com_node(ch)
            else:
                self.syntaxerror( 'unknown node type: %s' % tok, tok )
        return CallFunc(primaryNode, args, star_node, dstar_node,
                        lineno=extractLineNo(nodelist))

    def com_argument(self, nodelist, kw):
        if len(nodelist) == 3 and nodelist[2][0] == symbol.gen_for:
            test = self.com_node(nodelist[1])
            return 0, self.com_generator_expression(test, nodelist[2])
        if len(nodelist) == 2:
            if kw:
                self.syntaxerror( "non-keyword arg after keyword arg", nodelist )
            return 0, self.com_node(nodelist[1])
        result = self.com_node(nodelist[3])
        n = nodelist[1]
        while len(n) == 2 and n[0] != stable_parser.tokens['NAME']:
            n = n[1]
        if n[0] != stable_parser.tokens['NAME']:
            self.syntaxerror( "keyword can't be an expression (%s)"%n[0], n)
        node = Keyword(n[1], result, lineno=n[2])
        return 1, node

    def com_subscriptlist(self, primary, nodelist, assigning):
        # slicing:      simple_slicing | extended_slicing
        # simple_slicing:   primary "[" short_slice "]"
        # extended_slicing: primary "[" slice_list "]"
        # slice_list:   slice_item ("," slice_item)* [","]

        # backwards compat slice for '[i:j]'
        if len(nodelist) == 2:
            sub = nodelist[1]
            if (sub[1][0] == stable_parser.tokens['COLON'] or \
                            (len(sub) > 2 and sub[2][0] == stable_parser.tokens['COLON'])) and \
                            sub[-1][0] != symbol.sliceop:
                return self.com_slice(primary, sub, assigning)

        subscripts = []
        for i in range(1, len(nodelist), 2):
            subscripts.append(self.com_subscript(nodelist[i]))
        return Subscript(primary, assigning, subscripts,
                         lineno=extractLineNo(nodelist))

    def com_subscript(self, node):
        # slice_item: expression | proper_slice | ellipsis
        ch = node[1]
        t = ch[0]
        if t == stable_parser.tokens['DOT'] and node[2][0] == stable_parser.tokens['DOT']:
            return Ellipsis()
        if t == stable_parser.tokens['COLON'] or len(node) > 2:
            return self.com_sliceobj(node)
        return self.com_node(ch)

    def com_sliceobj(self, node):
        # proper_slice: short_slice | long_slice
        # short_slice:  [lower_bound] ":" [upper_bound]
        # long_slice:   short_slice ":" [stride]
        # lower_bound:  expression
        # upper_bound:  expression
        # stride:       expression
        #
        # Note: a stride may be further slicing...

        items = []

        if node[1][0] == stable_parser.tokens['COLON']:
            items.append(Const(None))
            i = 2
        else:
            items.append(self.com_node(node[1]))
            # i == 2 is a COLON
            i = 3

        if i < len(node) and node[i][0] == symbol.test:
            items.append(self.com_node(node[i]))
            i = i + 1
        else:
            items.append(Const(None))

        # a short_slice has been built. look for long_slice now by looking
        # for strides...
        for j in range(i, len(node)):
            ch = node[j]
            if len(ch) == 2:
                items.append(Const(None))
            else:
                items.append(self.com_node(ch[2]))
        return Sliceobj(items, lineno=extractLineNo(node))

    def com_slice(self, primary, node, assigning):
        # short_slice:  [lower_bound] ":" [upper_bound]
        lower = upper = None
        if len(node) == 3:
            if node[1][0] == stable_parser.tokens['COLON']:
                upper = self.com_node(node[2])
            else:
                lower = self.com_node(node[1])
        elif len(node) == 4:
            lower = self.com_node(node[1])
            upper = self.com_node(node[3])
        return Slice(primary, assigning, lower, upper,
                     lineno=extractLineNo(node))

    def get_docstring(self, node, n=None):
        if n is None:
            n = node[0]
            node = node[1:]
        if n == symbol.suite:
            if len(node) == 1:
                return self.get_docstring(node[0])
            for sub in node:
                if sub[0] == symbol.stmt:
                    return self.get_docstring(sub)
            return None
        if n == symbol.file_input:
            for sub in node:
                if sub[0] == symbol.stmt:
                    return self.get_docstring(sub)
            return None
        if n == symbol.atom:
            if node[0][0] == stable_parser.tokens['STRING']:
                s = ''
                for t in node:
                    s = s + eval(t[1])
                return s
            return None
        if n == symbol.stmt or n == symbol.simple_stmt \
           or n == symbol.small_stmt:
            return self.get_docstring(node[0])
        if n in _doc_nodes and len(node) == 1:
            return self.get_docstring(node[0])
        return None


_doc_nodes = [
    symbol.expr_stmt,
    symbol.testlist,
    symbol.testlist_safe,
    symbol.test,
    symbol.old_test,
    symbol.or_test,
    symbol.and_test,
    symbol.not_test,
    symbol.comparison,
    symbol.expr,
    symbol.xor_expr,
    symbol.and_expr,
    symbol.shift_expr,
    symbol.arith_expr,
    symbol.term,
    symbol.factor,
    symbol.power,
    ]

# comp_op: '<' | '>' | '=' | '>=' | '<=' | '<>' | '!=' | '=='
#             | 'in' | 'not' 'in' | 'is' | 'is' 'not'
_cmp_types = {
    stable_parser.tokens['LESS'] : '<',
    stable_parser.tokens['GREATER'] : '>',
    stable_parser.tokens['EQEQUAL'] : '==',
    stable_parser.tokens['EQUAL'] : '==',
    stable_parser.tokens['LESSEQUAL'] : '<=',
    stable_parser.tokens['GREATEREQUAL'] : '>=',
    stable_parser.tokens['NOTEQUAL'] : '!=',
    }

_assign_types = [
    symbol.test,
    symbol.old_test,
    symbol.or_test,
    symbol.and_test,
    symbol.not_test,
    symbol.comparison,
    symbol.expr,
    symbol.xor_expr,
    symbol.and_expr,
    symbol.shift_expr,
    symbol.arith_expr,
    symbol.term,
    symbol.factor,
    ]

# import types
# _names = {}
# for k, v in sym_name.items():
#     _names[k] = v
# for k, v in token.tok_name.items():
#     _names[k] = v
# 
# def debug_tree(tree):
#     l = []
#     for elt in tree:
#         if type(elt) == types.IntType:
#             l.append(_names.get(elt, elt))
#         elif type(elt) == types.StringType:
#             l.append(elt)
#         else:
#             l.append(debug_tree(elt))
#     return l
