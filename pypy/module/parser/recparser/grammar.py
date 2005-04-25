"""
a generic recursive descent parser
the grammar is defined as a composition of objects
the objects of the grammar are :
Alternative : as in S -> A | B | C
Sequence    : as in S -> A B C
KleenStar   : as in S -> A* or S -> A+
Token       : a lexer token
"""

DEBUG = 0

#### Abstract interface for a lexer/tokenizer
class TokenSource(object):
    """Abstract base class for a source tokenizer"""
    def context(self):
        """Returns a context to restore the state of the object later"""

    def restore(self, ctx):
        """Restore the context"""

    def next(self):
        """Returns the next token from the source
        a token is a tuple : (type,value) or (None,None) if the end of the
        source has been found
        """

    def current_line(self):
        """Returns the current line number"""
        return 0


######################################################################

from syntaxtree import SyntaxNode, TempSyntaxNode, TokenNode

class BaseGrammarBuilder(object):
    """Base/default class for a builder"""
    def __init__( self, rules=None, debug=0):
        self.rules = rules or {} # a dictionary of grammar rules for debug/reference
        self.debug = debug
        self.stack = []

    def context(self):
        """Returns the state of the builder to be restored later"""
        #print "Save Stack:", self.stack
        return len(self.stack)

    def restore(self, ctx):
        del self.stack[ctx:]
        #print "Restore Stack:", self.stack
        
    def alternative(self, rule, source):
        # Do nothing, keep rule on top of the stack
        if rule.is_root():
            elems = self.stack[-1].expand()
            self.stack[-1] = SyntaxNode(rule.name, source, *elems)
            if self.debug:
                self.stack[-1].dumpstr()
        return True

    def sequence(self, rule, source, elts_number):
        """ """
        items = []
        for node in self.stack[-elts_number:]:
            items += node.expand()
        if rule.is_root():
            node_type = SyntaxNode
        else:
            node_type = TempSyntaxNode
        # replace N elements with 1 element regrouping them
        if elts_number >= 1:
            elem = node_type(rule.name, source, *items)
            del self.stack[-elts_number:]
            self.stack.append(elem)
        elif elts_number == 0:
            self.stack.append(node_type(rule.name, source))
        if self.debug:
            self.stack[-1].dumpstr()
        return True

    def token(self, name, value, source):
        self.stack.append(TokenNode(name, source, value))
        if self.debug:
            self.stack[-1].dumpstr()
        return True


######################################################################
# Grammar Elements Classes (Alternative, Sequence, KleenStar, Token) #
######################################################################
class GrammarElement(object):
    """Base parser class"""
    def __init__(self, name):
        # the rule name
        self.name = name
        self.args = []
        self._is_root = False

    def is_root(self):
        """This is a root node of the grammar, that is one that will
        be included in the syntax tree"""
        if self.name!=":" and self.name.startswith(":"):
            return False
        return True

    def match(self, source, builder):
        """Try to match a grammar rule

        If next set of tokens matches this grammar element, use <builder>
        to build an appropriate object, otherwise returns None.

        /!\ If the sets of element didn't match the current grammar
        element, then the <source> is restored as it was before the
        call to the match() method
        """
        return None
    
    def __str__(self):
        return self.display(0)

    def __repr__(self):
        return self.display(0)

    def display(self, level):
        """Helper function used to represent the grammar.
        mostly used for debugging the grammar itself"""
        return "GrammarElement"


    def debug_return(self, ret, *args ):
        # FIXME: use a wrapper of match() methods instead of debug_return()
        #        to prevent additional indirection
        if ret and DEBUG>0:
            sargs = ",".join( [ str(i) for i in args ] )
            print "matched %s (%s): %s" % (self.__class__.__name__, sargs, self.display() )
        return ret

class Alternative(GrammarElement):
    """Represents an alternative in a grammar rule (as in S -> A | B | C)"""
    def __init__(self, name, *args):
        GrammarElement.__init__(self, name )
        self.args = list(args)
        for i in self.args:
            assert isinstance( i, GrammarElement )

    def match(self, source, builder):
        """If any of the rules in self.args matches
        returns the object built from the first rules that matches
        """
        if DEBUG>1:
            print "try alt:", self.display()
        for rule in self.args:
            m = rule.match( source, builder )
            if m:
                ret = builder.alternative( self, source )
                return self.debug_return( ret )
        return False

    def display(self, level=0):
        if level==0:
            name =  self.name + " -> "
        elif not self.name.startswith(":"):
            return self.name
        else:
            name = ""
        items = [ a.display(1) for a in self.args ]
        return name+"(" + "|".join( items ) + ")"
        

class Sequence(GrammarElement):
    """Reprensents a Sequence in a grammar rule (as in S -> A B C)"""
    def __init__(self, name, *args):
        GrammarElement.__init__(self, name )
        self.args = list(args)
        for i in self.args:
            assert isinstance( i, GrammarElement )

    def match(self, source, builder):
        """matches all of the symbols in order"""
        if DEBUG>1:
            print "try seq:", self.display()
        ctx = source.context()
        bctx = builder.context()
        for rule in self.args:
            m = rule.match(source, builder)
            if not m:
                # Restore needed because some rules may have been matched
                # before the one that failed
                source.restore(ctx)
                builder.restore(bctx)
                return None
        ret = builder.sequence(self, source, len(self.args))
        return self.debug_return( ret )

    def display(self, level=0):
        if level == 0:
            name = self.name + " -> "
        elif not self.name.startswith(":"):
            return self.name
        else:
            name = ""
        items = [a.display(1) for a in self.args]
        return name + "(" + " ".join( items ) + ")"

class KleenStar(GrammarElement):
    """Represents a KleenStar in a grammar rule as in (S -> A+) or (S -> A*)"""
    def __init__(self, name, _min = 0, _max = -1, rule=None):
        GrammarElement.__init__( self, name )
        self.args = [rule]
        self.min = _min
        if _max == 0:
            raise ValueError("KleenStar needs max==-1 or max>1")
        self.max = _max
        self.star = "x"

    def match(self, source, builder):
        """matches a number of times self.args[0]. the number must be comprised
        between self._min and self._max inclusive. -1 is used to represent infinity"""
        if DEBUG>1:
            print "try kle:", self.display()
        ctx = source.context()
        bctx = builder.context()
        rules = 0
        rule = self.args[0]
        while True:
            m = rule.match(source, builder)
            if not m:
                # Rule should be matched at least 'min' times
                if rules<self.min:
                    source.restore(ctx)
                    builder.restore(bctx)
                    return None
                ret = builder.sequence(self, source, rules)
                return self.debug_return( ret, rules )
            rules += 1
            if self.max>0 and rules == self.max:
                ret = builder.sequence(self, source, rules)
                return self.debug_return( ret, rules )

    def display(self, level=0):
        if level==0:
            name =  self.name + " -> "
        elif not self.name.startswith(":"):
            return self.name
        else:
            name = ""
        star = "{%d,%d}" % (self.min,self.max)
        if self.min==0 and self.max==1:
            star = "?"
        elif self.min==0 and self.max==-1:
            star = "*"
        elif self.min==1 and self.max==-1:
            star = "+"
        s = self.args[0].display(1)
        return name + "%s%s" % (s, star)

            
class Token(GrammarElement):
    """Represents a Token in a grammar rule (a lexer token)"""
    def __init__( self, name, value = None):
        GrammarElement.__init__( self, name )
        self.value = value

    def match(self, source, builder):
        """Matches a token.
        the default implementation is to match any token whose type
        corresponds to the object's name. You can extend Token
        to match anything returned from the lexer. for exemple
        type, value = source.next()
        if type=="integer" and int(value)>=0:
            # found
        else:
            # error unknown or negative integer
        """
        ctx = source.context()
        tk_type, tk_value = source.next()
        if tk_type==self.name:
            if self.value is None:
                ret = builder.token( tk_type, tk_value, source )
                return self.debug_return( ret, tk_type )
            elif self.value == tk_value:
                ret = builder.token( tk_type, tk_value, source )
                return self.debug_return( ret, tk_type, tk_value )
        if DEBUG>1:
            print "tried tok:", self.display()
        source.restore( ctx )
        return None

    def display(self, level=0):
        if self.value is None:
            return "<%s>" % self.name
        else:
            return "<%s>=='%s'" % (self.name, self.value)
    

