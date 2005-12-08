class AppTest_CompilerHooks:

    def test_basic_hook(self):
        # define the hook
        def threebecomestwo(ast, enc):
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
