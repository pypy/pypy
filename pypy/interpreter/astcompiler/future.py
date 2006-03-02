"""Parser for future statements

"""
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.interpreter.astcompiler import ast

def is_future(stmt):
    """Return true if statement is a well-formed future statement"""
    if not isinstance(stmt, ast.From):
        return 0
    if stmt.modname == "__future__":
        return 1
    else:
        return 0

class FutureParser(ast.ASTVisitor):

    features = ("nested_scopes", "generators", "division", "with_statement")

    def __init__(self):
        self.found = {} # set

    def visitModule(self, node):
        stmt = node.node
        invalid = False
        assert isinstance(stmt, ast.Stmt)
        for s in stmt.nodes:
            if not self.check_stmt(s, invalid):
                invalid = True

    def check_stmt(self, stmt, invalid):
        if isinstance(stmt, ast.From):
            stmt.valid_future = 0
            if invalid:
                return 0
            if is_future(stmt):
                assert isinstance(stmt, ast.From)
                for name, asname in stmt.names:
                    if name in self.features:
                        self.found[name] = 1
                    elif name=="*":
                        raise SyntaxError(
                            "future statement does not support import *",
                            filename = stmt.filename,
                            lineno = stmt.lineno)
                    else:
                        raise SyntaxError(
                            "future feature %s is not defined" % name,
                            filename = stmt.filename,
                            lineno = stmt.lineno)                        
                stmt.valid_future = 1
                return 1
        return 0

    def get_features(self):
        """Return list of features enabled by future statements"""
        return self.found.keys()

class BadFutureParser(ast.ASTVisitor):
    """Check for invalid future statements
    Those not marked valid are appearing after other statements
    """

    def visitModule(self, node):
        stmt = node.node
        assert isinstance(stmt, ast.Stmt)        
        for s in stmt.nodes:
            if isinstance(s, ast.From):
                if s.valid_future:
                    continue
                self.visitFrom(s)
            else:
                self.default(s)

    def visitFrom(self, node):
        if node.modname != "__future__":
            return
        raise SyntaxError( "from __future__ imports must occur at the beginning of the file",
                           filename=node.filename,
                           lineno=node.lineno)

def find_futures(node):
    p1 = FutureParser()
    p2 = BadFutureParser()
    node.accept( p1 )
    node.accept( p2 )
    return p1.get_features()

if __name__ == "__main__":
    import sys
    from pypy.interpreter.astcompiler import parseFile

    for file in sys.argv[1:]:
        print file
        tree = parseFile(file)
        v = FutureParser()
        tree.accept(v)
        print v.found
        print
