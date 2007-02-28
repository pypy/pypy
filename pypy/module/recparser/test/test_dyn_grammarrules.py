from pypy.conftest import gettestobjspace

class AppTest_InsertGrammarRules:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('dyngram', 'recparser'))
        cls.space = space

    def test_do_while(self):
        import dyngram, parser

        newrules = """
        compound_stmt: if_stmt | on_stmt | unless_stmt | dountil_stmt | while_stmt | for_stmt | try_stmt | with_stmt | funcdef | classdef
        dountil_stmt: 'do' ':' suite 'until' test
        unless_stmt: 'unless' test ':' suite
        on_stmt: 'on' NAME '=' test ':' suite ['else' ':' suite]
        """

        def build_dountil_stmt(items):
            """ 'do' ':' suite 'until' ':' test """
            lineno = items[0].lineno
            suite = items[2]
            test = items[-1]
            while_stmt = parser.ASTWhile(parser.ASTNot(test), suite, None, lineno)
            return parser.ASTStmt([suite, while_stmt], lineno)

        def build_unless_stmt(its):
            """ 'unless' test ':' suite  """
            lineno = its[0].lineno
            return parser.ASTIf([(parser.ASTNot(its[1]), its[3])], None, lineno)

        def make_assignment(var, node):
            # XXX: consts.OP_APPLY
            return parser.ASTAssign([parser.ASTAssName('x', 0)], node)

        def build_on_stmt(items):
            """ 'on' NAME = test ':' suite  'else' ':' suite"""
            varname = items[1].value
            test = items[3]
            suite = items[5]
            assign = make_assignment(varname, test)
            if len(items) == 9:
                else_ = items[-1]
            else:
                else_ = None
            test = parser.ASTIf([(parser.ASTName(varname), suite)], else_, items[0].lineno)
            return parser.ASTStmt([assign, test], items[0].lineno)

        dyngram.insert_grammar_rule(newrules, {'dountil_stmt' : build_dountil_stmt,
                                               'unless_stmt': build_unless_stmt,
                                               'on_stmt' : build_on_stmt,
                                               })

        # now we should be able to use do...until and unless statements
        d = {}
        exec '''
a = 0
do:
    a += 1
until True

b = 0
unless a == 2: b = 3
        ''' in d
        assert d['a'] == 1
        assert d['b'] == 3

