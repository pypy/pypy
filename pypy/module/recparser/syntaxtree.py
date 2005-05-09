import symbol
import token

TOKEN_MAP = {
    "STRING" : token.STRING,
    "NUMBER" : token.NUMBER,
    "NAME" : token.NAME,
    "NEWLINE" : token.NEWLINE,
    "DEDENT" : token.DEDENT,
    "ENDMARKER" : token.ENDMARKER,
    "INDENT" : token.INDENT,
    "NEWLINE" : token.NEWLINE,
    "NT_OFFSET" : token.NT_OFFSET,
    "N_TOKENS" : token.N_TOKENS,
    "OP" : token.OP,
    "?ERRORTOKEN" : token.ERRORTOKEN,
    "&" : token.AMPER,
    "&=" : token.AMPEREQUAL,
    "`" : token.BACKQUOTE,
    "^" : token.CIRCUMFLEX,
    "^=" : token.CIRCUMFLEXEQUAL,
    ":" : token.COLON,
    "," : token.COMMA,
    "." : token.DOT,
    "//" : token.DOUBLESLASH,
    "//=" : token.DOUBLESLASHEQUAL,
    "**" : token.DOUBLESTAR,
    "**=" : token.DOUBLESTAREQUAL,
    "==" : token.EQEQUAL,
    "=" : token.EQUAL,
    ">" : token.GREATER,
    ">=" : token.GREATEREQUAL,
    "{" : token.LBRACE,
    "}" : token.RBRACE,
    "<<" : token.LEFTSHIFT,
    "<<=" : token.LEFTSHIFTEQUAL,
    "<" : token.LESS,
    "<=" : token.LESSEQUAL,
    "(" : token.LPAR,
    "[" : token.LSQB,
    "-=" : token.MINEQUAL,
    "-" : token.MINUS,
    "!=" : token.NOTEQUAL,
    "<>" : token.NOTEQUAL,
    "%" : token.PERCENT,
    "%=" : token.PERCENTEQUAL,
    "+" : token.PLUS,
    "+=" : token.PLUSEQUAL,
    ")" : token.RBRACE,
    ">>" : token.RIGHTSHIFT,
    ">>=" : token.RIGHTSHIFTEQUAL,
    ")" : token.RPAR,
    "]" : token.RSQB,
    ";" : token.SEMI,
    "/" : token.SLASH,
    "/=" : token.SLASHEQUAL,
    "*" : token.STAR,
    "*=" : token.STAREQUAL,
    "~" : token.TILDE,
    "|" : token.VBAR,
    "|=" : token.VBAREQUAL,
    }
    
SYMBOLS = {}
# copies the numerical mapping between symbol name and symbol value
# into SYMBOLS
for k,v in symbol.__dict__.items():
    if type(v)==int:
        SYMBOLS[k] = v


class SyntaxNode(object):
    """A syntax node"""
    def __init__(self, name, source, *args):
        self.name = name
        self.nodes = list(args)
        self.lineno = source.current_line()
        
    def dumptree(self, treenodes, indent):
        treenodes.append(self.name)
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
        treenodes = []
        self.dumptree(treenodes, "")
        return "".join(treenodes)

    def __repr__(self):
        return "<node [%s] at 0x%x>" % (self.name, id(self))

    def __str__(self):
        return "(%s)"  % self.name

    def visit(self, visitor):
        visit_meth = getattr(visitor, "visit_%s" % self.name, None)
        if visit_meth:
            return visit_meth(self)
        # helper function for nodes that have only one subnode:
        if len(self.nodes) == 1:
            return self.nodes[0].visit(visitor)
        raise RuntimeError("Unknonw Visitor for %r" % self.name)

    def expand(self):
        return [ self ]

    def totuple(self, lineno=False ):
        symvalue = SYMBOLS.get( self.name, (0,self.name) )
        l = [ symvalue ]
        l += [node.totuple(lineno) for node in self.nodes]
        return tuple(l)
    

class TempSyntaxNode(SyntaxNode):
    """A temporary syntax node to represent intermediate rules"""
    def expand(self):
        return self.nodes

class TokenNode(SyntaxNode):
    """A token node"""
    def __init__(self, name, source, value):
        SyntaxNode.__init__(self, name, source)
        self.value = value

    def dumptree(self, treenodes, indent):
        if self.value:
            treenodes.append("%s='%s' (%d) " % (self.name, self.value, self.lineno))
        else:
            treenodes.append("'%s' (%d) " % (self.name, self.lineno))

    def __repr__(self):
        if self.value is not None:
            return "<%s=%s>" % ( self.name, repr(self.value))
        else:
            return "<%s!>" % (self.name,)

    def totuple(self, lineno=False):
        num = TOKEN_MAP.get(self.name, -1)
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
