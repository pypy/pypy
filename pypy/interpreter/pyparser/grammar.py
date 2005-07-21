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
USE_LOOKAHEAD = True

def get_symbol( codename, symbols ):
    """Helper function to build a token name"""
    if codename in symbols:
        return symbols[codename]
    else:
        return "["+str(codename)+"]"

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

    def offset(self, ctx=None):
        """Returns the position we're at so far in the source
        optionnally provide a context and you'll get the offset
        of the context"""
        return -1

    def current_line(self):
        """Returns the current line number"""
        return 0

    def get_pos(self):
        """Returns the current source position of the scanner"""
        return 0

    def get_source_text(self, pos1, pos2 ):
        """Returns the source text between two scanner positions"""
        return ""


######################################################################


def build_first_sets(rules):
    """builds the real first tokens set for each rule in <rules>

    Because a rule can be recursive (directly or indirectly), the
    *simplest* algorithm to build each first set is to recompute them
    until Computation(N) = Computation(N-1), N being the number of rounds.
    As an example, on Python2.3's grammar, we need 19 cycles to compute
    full first sets.
    """
    changed = True
    while changed:
        # loop while one first set is changed
        changed = False
        for rule in rules:
            # For each rule, recompute first set
            size = len(rule.first_set)
            rule.calc_first_set()
            new_size = len(rule.first_set)
            if new_size != size:
                changed = True
    for r in rules:
        assert len(r.first_set) > 0, "Error: ot Empty firstset for %s" % r
        r.reorder_rule()


from syntaxtree import SyntaxNode, TempSyntaxNode, TokenNode
#
# we use the term root for a grammar rule to specify rules that are given a name
# by the grammar
# a rule like S -> A B* is mapped as Sequence( SCODE, KleenStar(-3, B))
# so S is a root and the subrule describing B* is not.
# SCODE is the numerical value for rule "S"
class BaseGrammarBuilder(object):
    """Base/default class for a builder"""
    def __init__(self, rules=None, debug=0, symbols={} ):
        # a dictionary of grammar rules for debug/reference
        self.rules = rules or {}
        # This attribute is here for convenience
        self.source_encoding = None
        self.debug = debug
        self.stack = []
        self.symbols = symbols # mapping from codename to symbols

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
            self.stack[-1] = SyntaxNode(rule.codename, source, elems)
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
            elem = node_type(rule.codename, source, items)
            del self.stack[-elts_number:]
            self.stack.append(elem)
        elif elts_number == 0:
            self.stack.append(node_type(rule.codename, source, []))
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

    symbols = {} # dirty trick to provide a symbols mapping while printing (and not putting it in every object)
    
    def __init__(self, codename):
        # the rule name
        #assert type(codename)==int
        self.codename = codename # integer mapping to either a token value or rule symbol value
        self.args = []
        self.first_set = []
        self.first_set_complete = False
        # self._processing = False
        self._trace = False

    def is_root(self):
        """This is a root node of the grammar, that is one that will
        be included in the syntax tree"""
        # code attributed to root grammar rules are >=0
        if self.codename >=0:
            return True
        return False
    

    def match(self, source, builder, level=0):
        """Try to match a grammar rule

        If next set of tokens matches this grammar element, use <builder>
        to build an appropriate object, otherwise returns None.

        /!\ If the sets of element didn't match the current grammar
        element, then the <source> is restored as it was before the
        call to the match() method

        returns None if no match or an object build by builder
        """
        if not USE_LOOKAHEAD:
            return self._match(source, builder, level)
        pos1 = -1 # make the annotator happy
        pos2 = -1 # make the annotator happy
        token = source.peek()
        if self._trace:
            pos1 = source.get_pos()
        in_first_set = self.match_first_set(token)
        if not in_first_set: # and not EmptyToken in self.first_set:
            if EmptyToken in self.first_set:
                ret = builder.sequence(self, source, 0 )
                if self._trace:
                    self._debug_display(token, level, 'eee', builder.symbols)
                return self.debug_return( ret, builder.symbols, 0 )
            if self._trace:
                self._debug_display(token, level, 'rrr', builder.symbols)
            return 0
        elif self._trace:
            self._debug_display(token, level, '>>>', builder.symbols)
        
        res = self._match(source, builder, level)
        if self._trace:
            pos2 = source.get_pos()
            if res:
                prefix = '+++'
            else:
                prefix = '---'
            self._debug_display(token, level, prefix, builder.symbols)
            print ' '*level, prefix, " TEXT ='%s'" % (
                source.get_source_text(pos1,pos2))
            if res:
                print "*" * 50
        return res

    def _debug_display(self, token, level, prefix, symbols):
        """prints context debug informations"""
        prefix = '%s%s' % (' ' * level, prefix)
        print prefix, " RULE =", self
        print prefix, " TOKEN =", token
        print prefix, " FIRST SET =", self.first_set
        
        
    def _match(self, source, builder, level=0):
        """Try to match a grammar rule

        If next set of tokens matches this grammar element, use <builder>
        to build an appropriate object, otherwise returns 0.

        /!\ If the sets of element didn't match the current grammar
        element, then the <source> is restored as it was before the
        call to the match() method

        returns None if no match or an object build by builder
        """
        return 0
    
    def parse(self, source):
        """Returns a simplified grammar if the rule matched at the source
        current context or None"""
        # **NOT USED** **NOT IMPLEMENTED**
        # To consider if we need to improve speed in parsing
        pass

    def __str__(self):
        return self.display(0, GrammarElement.symbols )

    def __repr__(self):
        return self.display(0, GrammarElement.symbols )

    def display(self, level=0, symbols={}):
        """Helper function used to represent the grammar.
        mostly used for debugging the grammar itself"""
        return "GrammarElement"


    def debug_return(self, ret, symbols, *args ):
        # FIXME: use a wrapper of match() methods instead of debug_return()
        #        to prevent additional indirection
        if ret and DEBUG > 0:
            sargs = ",".join( [ str(i) for i in args ] )
            print "matched %s (%s): %s" % (self.__class__.__name__,
                                           sargs, self.display(0, symbols=symbols) )
        return ret

    
    def calc_first_set(self):
        """returns the list of possible next tokens
        *must* be implemented in subclasses
        """
        # XXX: first_set could probably be implemented with sets
        return []

    def match_first_set(self, other):
        """matching is not equality:
        token('NAME','x') matches token('NAME',None)
        """
        for tk in self.first_set:
            if tk.match_token( other ):
                return True
        return False

    def in_first_set(self, other):
        return other in self.first_set

    def reorder_rule(self):
        """Called after the computation of first set to allow rules to be
        reordered to avoid ambiguities
        """
        pass

class Alternative(GrammarElement):
    """Represents an alternative in a grammar rule (as in S -> A | B | C)"""
    def __init__(self, name, args):
        GrammarElement.__init__(self, name )
        self.args = args
        self._reordered = False
        for i in self.args:
            assert isinstance( i, GrammarElement )

    def _match(self, source, builder, level=0 ):
        """If any of the rules in self.args matches
        returns the object built from the first rules that matches
        """
        if DEBUG > 1:
            print "try alt:", self.display(level, builder.symbols )
        tok = source.peek()
        # Here we stop at the first match we should
        # try instead to get the longest alternative
        # to see if this solve our problems with infinite recursion
        for rule in self.args:
            if USE_LOOKAHEAD:
                if not rule.match_first_set(tok) and EmptyToken not in rule.first_set:
                    if self._trace:
                        print "Skipping impossible rule: %s" % (rule,)
                    continue
            m = rule.match(source, builder, level+1)
            if m:
                ret = builder.alternative( self, source )
                return self.debug_return( ret, builder.symbols )
        return 0

    def display(self, level=0, symbols={}):
        name = get_symbol( self.codename, symbols )
        if level == 0:
            name =  name + " -> "
        elif self.is_root():
            return name
        else:
            name = ""
        items = [ a.display(1,symbols) for a in self.args ]
        return name+"(" + "|".join( items ) + ")"

    def calc_first_set(self):
        """returns the list of possible next tokens
        if S -> (A | B | C):
            LAH(S) = Union( LAH(A), LAH(B), LAH(C) )
        """
        # do this to avoid problems on indirect recursive rules
        for rule in self.args:
            for t in rule.first_set:
                if t not in self.first_set:
                    self.first_set.append(t)
                # self.first_set[t] = 1

    def reorder_rule(self):
        # take the opportunity to reorder rules in alternatives
        # so that rules with Empty in their first set come last
        # warn if two rules have empty in their first set
        empty_set = []
        not_empty_set = []
        # <tokens> is only needed for warning / debugging purposes
        tokens_set = []
        for rule in self.args:
            if EmptyToken in rule.first_set:
                empty_set.append(rule)
            else:
                not_empty_set.append(rule)
            if DEBUG:
                # This loop is only neede dfor warning / debugging purposes
                # It will check if a token is part of several first sets of
                # a same alternative
                for token in rule.first_set:
                    if token is not EmptyToken and token in tokens_set:
                        print "Warning, token %s in\n\t%s's first set is " \
                            " part of a previous rule's first set in " \
                            " alternative\n\t%s" % (token, rule, self)
                    tokens_set.append(token)
        if len(empty_set) > 1 and not self._reordered:
            print "Warning: alternative %s has more than one rule " \
                "matching Empty" % self
            self._reordered = True
        self.args[:] = not_empty_set
        self.args.extend( empty_set )

    
class Sequence(GrammarElement):
    """Reprensents a Sequence in a grammar rule (as in S -> A B C)"""
    def __init__(self, name, args):
        GrammarElement.__init__(self, name )
        self.args = args
        for i in self.args:
            assert isinstance( i, GrammarElement )

    def _match(self, source, builder, level=0):
        """matches all of the symbols in order"""
        if DEBUG > 1:
            print "try seq:", self.display(level, builder.symbols )
        ctx = source.context()
        bctx = builder.context()
        for rule in self.args:
            m = rule.match(source, builder, level+1)
            if not m:
                # Restore needed because some rules may have been matched
                # before the one that failed
                source.restore(ctx)
                builder.restore(bctx)
                return 0
        ret = builder.sequence(self, source, len(self.args))
        return self.debug_return( ret, builder.symbols )

    def display(self, level=0, symbols={}):
        name = get_symbol( self.codename, symbols )
        if level ==  0:
            name = name + " -> "
        elif self.is_root():
            return name
        else:
            name = ""
        items = [a.display(1) for a in self.args]
        return name + "(" + " ".join( items ) + ")"

    def calc_first_set(self):
        """returns the list of possible next tokens
        if S -> A* B C:
            LAH(S) = Union( LAH(A), LAH(B) )
        if S -> A+ B C:
            LAH(S) = LAH(A)
        if S -> A B C:
            LAH(S) = LAH(A)
        """
        for rule in self.args:
            if not rule.first_set:
                break
            if EmptyToken in self.first_set:
                self.first_set.remove( EmptyToken )

                # del self.first_set[EmptyToken]
            # while we're in this loop, keep agregating possible tokens
            for t in rule.first_set:
                if t not in self.first_set:
                    self.first_set.append(t)
                # self.first_set[t] = 1
            if EmptyToken not in rule.first_set:
                break
                


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
        if self.min == 0:
            self.first_set.append( EmptyToken )
            # self.first_set[EmptyToken] = 1

    def _match(self, source, builder, level=0):
        """matches a number of times self.args[0]. the number must be
        comprised between self._min and self._max inclusive. -1 is used to
        represent infinity
        """
        if DEBUG > 1:
            print "try kle:", self.display()
        ctx = source.context()
        bctx = builder.context()
        rules = 0
        rule = self.args[0]
        while True:
            m = rule.match(source, builder, level+1)
            if not m:
                # Rule should be matched at least 'min' times
                if rules<self.min:
                    source.restore(ctx)
                    builder.restore(bctx)
                    return 0
                ret = builder.sequence(self, source, rules)
                return self.debug_return( ret, builder.symbols, rules )
            rules += 1
            if self.max>0 and rules == self.max:
                ret = builder.sequence(self, source, rules)
                return self.debug_return( ret, builder.symbols, rules )

    def display(self, level=0, symbols={}):
        name = get_symbol( self.codename, symbols )
        if level==0:
            name = name + " -> "
        elif self.is_root():
            return name
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


    def calc_first_set(self):
        """returns the list of possible next tokens
        if S -> A*:
            LAH(S) = Union( LAH(A), EmptyToken )
        if S -> A+:
            LAH(S) = LAH(A)
        """
        rule = self.args[0]
        self.first_set = rule.first_set[:]
        # self.first_set = dict(rule.first_set)
        if self.min == 0 and EmptyToken not in self.first_set:
            self.first_set.append(EmptyToken)
            # self.first_set[EmptyToken] = 1

class Token(GrammarElement):
    """Represents a Token in a grammar rule (a lexer token)"""
    def __init__( self, codename, value = None):
        GrammarElement.__init__( self, codename )
        self.value = value
        self.first_set = [self]
        # self.first_set = {self: 1}

    def match(self, source, builder, level=0):
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
        tk = source.next()
        if tk.codename == self.codename:
            if self.value is None:
                ret = builder.token( tk.codename, tk.value, source )
                return self.debug_return( ret, builder.symbols, tk.codename )
            elif self.value == tk.value:
                ret = builder.token( tk.codename, tk.value, source )
                return self.debug_return( ret, builder.symbols, tk.codename, tk.value )
        if DEBUG > 1:
            print "tried tok:", self.display()
        source.restore( ctx )
        return 0

    def display(self, level=0, symbols={}):
        name = get_symbol( self.codename, symbols )
        if self.value is None:
            return "<%s>" % name
        else:
            return "<%s>=='%s'" % (name, self.value)
    

    def match_token(self, other):
        """convenience '==' implementation, this is *not* a *real* equality test
        a Token instance can be compared to:
         - another Token instance in which case all fields (name and value)
           must be equal
         - a tuple, such as those yielded by the Python lexer, in which case
           the comparison algorithm is similar to the one in match()
        """
        if not isinstance(other, Token):
            raise RuntimeError("Unexpected token type %r" % other)
        if other is EmptyToken:
            return False
        res = other.codename == self.codename and self.value in (None, other.value)
        #print "matching", self, other, res
        return res
    
    def __eq__(self, other):
        return self.codename == other.codename and self.value == other.value
        

    
    def calc_first_set(self):
        """computes the list of possible next tokens
        """
        pass

from pypy.interpreter.pyparser.pytoken import NULLTOKEN
EmptyToken = Token(NULLTOKEN, None)
