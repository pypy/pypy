class AppTest_CompilerHooks:

    def test_basic_hook(self):
        # define the hook
        def threebecomestwo(ast, enc, filename):
            class ChangeConstVisitor:
                def visitConst(self, node):
                    if node.value == 3:
                        node.value = 2

                def defaultvisit(self, node):
                    for child in node.getChildNodes():
                        child.accept(self)

                def __getattr__(self, attrname):
                    if attrname.startswith('visit'):
                        return self.defaultvisit
                    raise AttributeError(attrname)
                
            ast.accept(ChangeConstVisitor())
            return ast

        # install the hook
        import parser
        parser.install_compiler_hook(threebecomestwo)
        d = {}
        exec "a = 3" in d
        assert d['a'] == 2 # well, yes ...

    def test_removal_of_broken_hooks(self):
        def hook(ast, enc, filename):
            1/0
        import parser
        parser.install_compiler_hook(hook)
        raises(ZeroDivisionError, "eval('1')")
        assert eval("1") == 1

        def hook2(ast, enc, filename):
            return 1
        parser.install_compiler_hook(hook2)
        raises(TypeError, "eval('2')")
        assert eval("2") == 2
        


class DISABLEDAppTest_GlobalsAsConsts:
    def test_ast_parser(self):
        # define the hook
        def change_globals(ast, enc, filename):
            class ChangeGlobalsVisitor:
                def visitConst(self, node):
                    pass

                def defaultvisit(self, node):
                    for child in node.getChildNodes():
                        child.accept(self)

                def __getattr__(self, attrname):
                    if attrname.startswith('visit'):
                        return self.defaultvisit
                    raise AttributeError(attrname)
                
            ast.accept(ChangeConstVisitor())
            return ast

        # install the hook
        import parser
        parser.install_compiler_hook(change_globals)
        # check that the visitor changed all globals
        # in the code into Consts
        # TODO
        # simplest version of the test : dis(code) | grep -v LOAD_GLOBAL == dis(code)
