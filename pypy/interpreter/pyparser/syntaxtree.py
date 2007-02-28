"""SyntaxTree class definition"""
# try:
# #    from pypy.interpreter.pyparser.pysymbol import sym_values
#     from pypy.interpreter.pyparser.pytoken import tok_values
# except ImportError:
# #    from pysymbol import sym_values
#     from pytoken import tok_values

from pypy.tool.uid import uid

from pypy.tool.uid import uid

class AbstractSyntaxVisitor(object):
    def visit_syntaxnode( self, node ):
        pass

    def visit_tempsyntaxnode( self, node ):
        pass

    def visit_tokennode( self, node ):
        pass

class SyntaxNode(object):
    """A syntax node"""
    def __init__(self, name, args, lineno=-1):
        self.name = name
        self.nodes = args
        self.lineno = lineno
        
    def dumptree(self, treenodes, indent):
        """helper function used to dump the syntax tree"""
        treenodes.append(str(self.name))
        if len(self.nodes) > 1:
            treenodes.append(" -> (\n")
            treenodes.append(indent+" ")
            for node in self.nodes:
                node.dumptree(treenodes, indent+" ")
            treenodes.append(")\n")
            treenodes.append(indent)
        elif len(self.nodes) == 1:
            treenodes.append(" ->\n")
            treenodes.append(indent+" ")
            self.nodes[0].dumptree(treenodes, indent+" ")

    def dumpstr(self):
        """turns the tree repr into a string"""
        treenodes = []
        self.dumptree(treenodes, "")
        return "".join(treenodes)

    def __repr__(self):
        return "<node [%s] at 0x%x>" % (self.name, uid(self))

    def __str__(self):
        return "(%s)" % self.name

    def visit(self, visitor):
        assert isinstance(visitor, AbstractSyntaxVisitor) 
        return visitor.visit_syntaxnode(self)

    def expand(self):
        """expand the syntax node to its content,
        do nothing here since we are a regular node and not
        a TempSyntaxNode"""
        return [ self ]

    def totuple(self, sym_values, lineno=False ):
        """returns a tuple representation of the syntax tree
        needs symbols+tokens value to name mapping to represent the nodes
        """
        symvalue = sym_values.get( self.name, (0, self.name) )
        l = [ symvalue ]
        l += [node.totuple(lineno, sym_values ) for node in self.nodes]
        return tuple(l)
    

class TempSyntaxNode(SyntaxNode):
    """A temporary syntax node to represent intermediate rules"""
    def expand(self):
        """expand the syntax node to its content"""
        return self.nodes

    def visit(self, visitor):
        assert isinstance(visitor, AbstractSyntaxVisitor) 
        return visitor.visit_tempsyntaxnode(self)

class TokenNode(SyntaxNode):
    """A token node"""
    def __init__(self, name, value, lineno = -1):
        SyntaxNode.__init__(self, name, [], lineno)
        self.value = value

    def dumptree(self, treenodes, indent):
        """helper function used to dump the syntax tree"""
        if self.value:
            treenodes.append("%s='%s' (%d) " % (self.name, self.value,
                                                self.lineno))
        else:
            treenodes.append("'%s' (%d) " % (self.name, self.lineno))

    def __repr__(self):
        if self.value is not None:
            return "<%s=%s>" % ( self.name, repr(self.value))
        else:
            return "<%s!>" % (self.name,)

    def visit(self, visitor):
        assert isinstance(visitor, AbstractSyntaxVisitor) 
        return visitor.visit_tokennode(self)

    def totuple(self, tok_values, lineno=False):
        """returns a tuple representation of the syntax tree
        needs symbols+tokens value to name mapping to represent the nodes
        """
        num = tok_values.get(self.name, -1)
        if num == -1:
            print "Unknown", self.name, self.value
        if self.value is not None:
            val = self.value
        else:
            if self.name not in ("NEWLINE", "INDENT", "DEDENT", "ENDMARKER"):
                val = self.name
            else:
                val = self.value or ''
        if lineno:
            return (num, val, self.lineno)
        else:
            return (num, val)
