"""
a generic recursive descent parser
the grammar is defined as a composition of objects
the objects of the grammar are :
Alternative : as in S -> A | B | C
Sequence    : as in S -> A B C
KleeneStar   : as in S -> A* or S -> A+
Token       : a lexer token
"""
try:
    from pypy.interpreter.baseobjspace import Wrappable
    from pypy.interpreter.pyparser.pytoken import NULLTOKEN
except ImportError:
    # allows standalone testing
    Wrappable = object
    NULLTOKEN = -1 # None


from syntaxtree import SyntaxNode, TempSyntaxNode, TokenNode


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

    def current_linesource(self):
        """Returns the current line"""
        return ""

    def current_lineno(self):
        """Returns the current line number"""
        return 0

    def get_pos(self):
        """Returns the current source position of the scanner"""
        return 0

    def get_source_text(self, pos1, pos2 ):
        """Returns the source text between two scanner positions"""
        return ""

    def peek(self):
        pass

######################################################################

class AbstractContext(object):
    """Abstract base class. derived objects put
    some attributes here that users can use to save
    restore states"""
    pass

class AbstractBuilder(Wrappable):
    """Abstract base class for builder objects"""
    def __init__(self, parser, debug=0 ):
        # This attribute is here for convenience
        self.debug = debug
        # the parser that represent the grammar used
        # Commented the assert: this eases the testing
        #assert isinstance( parser, Parser )
        self.parser = parser

    def context(self):
        """Return an opaque context object"""
        pass

    def restore(self, ctx):
        """Accept an opaque context object"""
        pass

    def alternative(self, rule, source):
        return False

    def sequence(self, rule, source, elts_number):
        return False

    def token(self, name, value, source):
        return False

#
# we use the term root for a grammar rule to specify rules that are given a name
# by the grammar
# a rule like S -> A B* is mapped as Sequence( SCODE, KleeneStar(-3, B))
# so S is a root and the subrule describing B* is not.
# SCODE is the numerical value for rule "S"

class BaseGrammarBuilderContext(AbstractContext):
    def __init__(self, stackpos ):
        self.stackpos = stackpos

class BaseGrammarBuilder(AbstractBuilder):
    """Base/default class for a builder"""
    # XXX (adim): this is trunk's keyword management
    keywords = None
    def __init__(self, parser, debug=0 ):
        AbstractBuilder.__init__(self, parser, debug )
        # stacks contain different objects depending on the builder class
        # to be RPython they should not be defined in the base class
        self.stack = []

    def context(self):
        """Returns the state of the builder to be restored later"""
        return BaseGrammarBuilderContext(len(self.stack))

    def restore(self, ctx):
        assert isinstance(ctx, BaseGrammarBuilderContext)
        del self.stack[ctx.stackpos:]

    def alternative(self, rule, source):
        # Do nothing, keep rule on top of the stack
        if rule.is_root():
            elems = self.stack[-1].expand()
            self.stack[-1] = SyntaxNode(rule.codename, elems, source.current_lineno())
            if self.debug:
                self.stack[-1].dumpstr()
        return True

    def sequence(self, rule, source, elts_number):
        """ """
        items = []
        slice_start = len(self.stack) - elts_number
        assert slice_start >= 0
        for node in self.stack[slice_start:]:
            items += node.expand()
        is_root = rule.is_root()
        # replace N elements with 1 element regrouping them
        if elts_number >= 1:
            if is_root:
                elem = SyntaxNode(rule.codename, items, source.current_lineno())
            else:
                elem = TempSyntaxNode(rule.codename, items, source.current_lineno())
            del self.stack[slice_start:]
            self.stack.append(elem)
        elif elts_number == 0:
            if is_root:
                self.stack.append(SyntaxNode(rule.codename, [], source.current_lineno()))
            else:
                self.stack.append(TempSyntaxNode(rule.codename, [], source.current_lineno()))

        if self.debug:
            self.stack[-1].dumpstr()
        return True

    def token(self, name, value, source):
        self.stack.append(TokenNode(name, value, source.current_lineno()))
        if self.debug:
            self.stack[-1].dumpstr()
        return True


#######################################################################
# Grammar Elements Classes (Alternative, Sequence, KleeneStar, Token) #
#######################################################################
class GrammarElement(Wrappable):
    """Base parser class"""

    _trace = False
    first_set = None
    emptytoken_in_first_set = False
    _match_cache = None
    args = []

    symbols = {} # dirty trick to provide a symbols mapping while printing (and not putting it in every object)

    _attrs_ = ['parser', 'codename', 'args',
               'first_set', 'emptytoken_in_first_set', '_match_cache']

    def __init__(self, parser, codename):
        # the rule name
        assert isinstance(parser, Parser)
        self.parser = parser
        # integer mapping to either a token value or rule symbol value
        self.codename = codename 

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
        if not in_first_set:
            if self.emptytoken_in_first_set:
                ret = builder.sequence(self, source, 0 )
                if self._trace:
                    self._debug_display(token, level, 'eee' )
                return ret
            if self._trace:
                self._debug_display(token, level, 'rrr' )
            return 0
        elif self._trace:
            self._debug_display(token, level, '>>>')

        res = self._match(source, builder, level)
        if self._trace:
            pos2 = source.get_pos()
            if res:
                prefix = '+++'
            else:
                prefix = '---'
            self._debug_display(token, level, prefix)
            print ' '*level, prefix, " TEXT ='%s'" % (
                source.get_source_text(pos1,pos2))
            if res:
                print "*" * 50
        return res

    def _debug_display(self, token, level, prefix):
        """prints context debug informations"""
        prefix = '%s%s' % (' ' * level, prefix)
        print prefix, " RULE =", self
        print prefix, " TOKEN =", token
        print prefix, " FIRST SET =", getattr(self, 'first_set', 'none')

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
        try:
            return self.display(0)
        except Exception, e:
            import traceback
            traceback.print_exc()

    def __repr__(self):
        try:
            return self.display(0)
        except Exception, e:
            import traceback
            traceback.print_exc()

    def display(self, level=0):
        """Helper function used to represent the grammar.
        mostly used for debugging the grammar itself"""
        return "GrammarElement"


    def debug_return(self, ret, arg="" ):
        # FIXME: use a wrapper of match() methods instead of debug_return()
        #        to prevent additional indirection even better a derived
        #        Debugging builder class
        if ret and DEBUG > 0:
            print "matched %s (%s): %s" % (self.__class__.__name__,
                                           arg, self.display(0) )
        return ret


    def calc_first_set(self):
        """returns the list of possible next tokens
        *must* be implemented in subclasses
        """
        pass

    def get_first_set(self):
        if self.first_set is None:
            self.initialize_first_set()
        return self.first_set

    def initialize_first_set(self):
        self.first_set = {}

    def optimize_first_set(self):
        """Precompute a data structure that optimizes match_first_set().
        The first_set attribute should no longer be needed after this.
        """
        self.emptytoken_in_first_set = self.parser.EmptyToken in self.first_set
        # see match_first_set() for the way this _match_cache is supposed
        # to be used
        self._match_cache = [GrammarElement._EMPTY_CODENAME_SET,  # share empty
                             GrammarElement._EMPTY_CODENAME_SET]  #       dicts
        for tk in self.first_set:
            if tk is not self.parser.EmptyToken:
                cache = self._match_cache[tk.isKeyword]
                if not cache:
                    cache = self._match_cache[tk.isKeyword] = {}   # new dict
                if tk.value is None:
                    cache[tk.codename] = None    # match any value
                else:
                    values = cache.setdefault(tk.codename, {})
                    if values is None:
                        pass    # already seen another tk matching any value
                    else:
                        values[tk.value] = None    # add tk.value to the set

    _EMPTY_CODENAME_SET = {}
    _EMPTY_VALUES_SET = {}

    def match_first_set(self, other):
        """matching is not equality:
        token('NAME','x') matches token('NAME',None).

        More precisely, for a match, we need to find a tk in self.first_set
        for which all the following is true:
          - other is not EmptyToken
          - other.isKeyword == tk.isKeyword
          - other.codename == tk.codename
          - other.value == tk.value or tk.value is None
        """
        cachelist = self._match_cache
        if cachelist is None:
            return True        # not computed yet
        cache = cachelist[other.isKeyword]
        values = cache.get(other.codename, GrammarElement._EMPTY_VALUES_SET)
        if values is None:
            return True          # 'None' means 'matches anything'
        elif other.value is None:
            return False         # because tk.value != None (for all tk)
        else:
            return other.value in values  # otherwise, ok only if in the set
            # XXX "None in dict" crashes after translation - needs to be fixed

    def reorder_rule(self):
        """Called after the computation of first set to allow rules to be
        reordered to avoid ambiguities
        """
        pass

    def validate( self, syntax_node ):
        """validate a syntax tree/subtree from this grammar node"""
        pass


class GrammarProxy(GrammarElement):
    def __init__(self, parser, rule_name, codename=-1 ):
        GrammarElement.__init__(self, parser, codename )
        self.rule_name = rule_name
        self.object = None

    def display(self, level=0):
        """Helper function used to represent the grammar.
        mostly used for debugging the grammar itself"""
        name = self.parser.symbol_repr(self.codename)
        repr = "Proxy("+name
        if self.object:
            repr+=","+self.object.display(1)
        repr += ")"
        return repr



class Alternative(GrammarElement):
    """Represents an alternative in a grammar rule (as in S -> A | B | C)"""
    def __init__(self, parser, name, args):
        GrammarElement.__init__(self, parser, name )
        self.args = args
        self._reordered = False
        for i in self.args:
            assert isinstance( i, GrammarElement )

    def _match(self, source, builder, level=0 ):
        """If any of the rules in self.args matches
        returns the object built from the first rules that matches
        """
        if DEBUG > 1:
            print "try alt:", self.display(level)
        tok = source.peek()
        # Here we stop at the first match we should
        # try instead to get the longest alternative
        # to see if this solve our problems with infinite recursion
        for rule in self.args:
            if USE_LOOKAHEAD:
                if not rule.match_first_set(tok) and not rule.emptytoken_in_first_set:
                    if self._trace:
                        print "Skipping impossible rule: %s" % (rule,)
                    continue
            m = rule.match(source, builder, level+1)
            if m:
                ret = builder.alternative( self, source )
                return ret
        return 0

    def display(self, level=0):
        name = self.parser.symbol_repr( self.codename )
        if level == 0:
            name =  name + " -> "
        elif self.is_root():
            return name
        else:
            name = ""
        items = [ a.display(1) for a in self.args ]
        return name+"(" + "|".join( items ) + ")"

    def calc_first_set(self):
        """returns the list of possible next tokens
        if S -> (A | B | C):
            LAH(S) = Union( LAH(A), LAH(B), LAH(C) )
        """
        # do this to avoid problems on indirect recursive rules
        for rule in self.args:
            for t in rule.get_first_set():
                self.first_set[t] = None

    def reorder_rule(self):
        # take the opportunity to reorder rules in alternatives
        # so that rules with Empty in their first set come last
        # warn if two rules have empty in their first set
        empty_set = []
        not_empty_set = []
        # <tokens> is only needed for warning / debugging purposes
        tokens_set = []
        for rule in self.args:
            if self.parser.EmptyToken in rule.first_set:
                empty_set.append(rule)
            else:
                not_empty_set.append(rule)
            if DEBUG:
                # This loop is only neede dfor warning / debugging purposes
                # It will check if a token is part of several first sets of
                # a same alternative
                for token in rule.first_set:
                    if token is not self.parser.EmptyToken and token in tokens_set:
                        print "Warning, token %s in\n\t%s's first set is " \
                            " part of a previous rule's first set in " \
                            " alternative\n\t%s" % (token, rule, self)
                    tokens_set.append(token)
        if len(empty_set) > 1 and not self._reordered:
            print "Warning: alternative %s has more than one rule " \
                "matching Empty" % self
            self._reordered = True
        # self.args[:] = not_empty_set
        for elt in self.args[:]:
            self.args.remove(elt)
        for elt in not_empty_set:
            self.args.append(elt)
        self.args.extend( empty_set )

    def validate( self, syntax_node ):
        """validate a syntax tree/subtree from this grammar node"""
        if self.codename != syntax_node.name:
            return False
        if len(syntax_node.nodes) != 1:
            return False
        node = syntax_node.nodes[0]
        for alt in self.args:
            if alt.validate( node ):
                return True
        return False



class Sequence(GrammarElement):
    """Reprensents a Sequence in a grammar rule (as in S -> A B C)"""
    def __init__(self, parser, name, args):
        GrammarElement.__init__(self, parser, name )
        self.args = args
        for i in self.args:
            assert isinstance( i, GrammarElement )


    def _match(self, source, builder, level=0):
        """matches all of the symbols in order"""
        if DEBUG > 1:
            print "try seq:", self.display(0)
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
        return ret

    def display(self, level=0):
        name = self.parser.symbol_repr( self.codename )
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
            if not rule.get_first_set():
                break
            if self.parser.EmptyToken in self.first_set:
                del self.first_set[self.parser.EmptyToken]
            # while we're in this loop, keep agregating possible tokens
            for t in rule.first_set:
                self.first_set[t] = None
            if self.parser.EmptyToken not in rule.first_set:
                break

    def validate( self, syntax_node ):
        """validate a syntax tree/subtree from this grammar node"""
        if self.codename != syntax_node.name:
            return False
        if len(syntax_node.nodes) != len(self.args):
            return False
        for i in xrange(len(self.args)):
            rule = self.args[i]
            node = syntax_node.nodes[i]
            if not rule.validate( node ):
                return False
        return True



class KleeneStar(GrammarElement):
    """Represents a KleeneStar in a grammar rule as in (S -> A+) or (S -> A*)"""
    def __init__(self, parser, name, _min = 0, _max = -1, rule=None):
        GrammarElement.__init__( self, parser, name )
        self.args = [rule]
        self.min = _min
        if _max == 0:
            raise ValueError("KleeneStar needs max==-1 or max>1")
        self.max = _max
        self.star = "x"

    def initialize_first_set(self):
        GrammarElement.initialize_first_set(self)
        if self.min == 0:
            self.first_set[self.parser.EmptyToken] = None

    def _match(self, source, builder, level=0):
        """matches a number of times self.args[0]. the number must be
        comprised between self._min and self._max inclusive. -1 is used to
        represent infinity
        """
        if DEBUG > 1:
            print "try kle:", self.display(0)
        ctx = None
        bctx = None
        if self.min:
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
                return ret
            rules += 1
            if self.max>0 and rules == self.max:
                ret = builder.sequence(self, source, rules)
                return ret

    def display(self, level=0):
        name = self.parser.symbol_repr( self.codename )
        if level==0:
            name = name + " -> "
        elif self.is_root():
            return name
        else:
            name = ""
        star = self.get_star()
        s = self.args[0].display(1)
        return name + "%s%s" % (s, star)

    def get_star(self):
        star = "{%d,%d}" % (self.min,self.max)
        if self.min==0 and self.max==1:
            star = "?"
        elif self.min==0 and self.max==-1:
            star = "*"
        elif self.min==1 and self.max==-1:
            star = "+"
        return star

    def calc_first_set(self):
        """returns the list of possible next tokens
        if S -> A*:
            LAH(S) = Union( LAH(A), self.parser.EmptyToken )
        if S -> A+:
            LAH(S) = LAH(A)
        """
        rule = self.args[0]
        self.first_set = rule.get_first_set().copy()
        if self.min == 0:
            self.first_set[self.parser.EmptyToken] = None

    def validate( self, syntax_node ):
        """validate a syntax tree/subtree from this grammar node"""
        if self.codename != syntax_node.name:
            return False
        rule = self.args[0]
        if self.min > len(syntax_node.nodes):
            return False
        if self.max>=0 and self.max<len(syntax_node.nodes):
            return False
        for n in self.node:
            if not rule.validate(n):
                return False
        return True


class Token(GrammarElement):
    """Represents a Token in a grammar rule (a lexer token)"""
    isKeyword = True
    _attrs_ = ['isKeyword', 'value']

    def __init__(self, parser, codename, value=None):
        GrammarElement.__init__(self, parser, codename)
        self.value = value

    def initialize_first_set(self):
        self.first_set = {self: None}

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
        # XXX (adim): this is trunk's keyword management
        # if (self.value is not None and builder.keywords is not None
        #     and self.value not in builder.keywords):
        #     return 0

        ctx = source.context()
        tk = source.next()
        if tk.codename == self.codename and tk.isKeyword:
            if self.value is None:
                ret = builder.token( tk.codename, tk.value, source )
                return ret
            elif self.value == tk.value:
                ret = builder.token( tk.codename, tk.value, source )
                return ret
        if DEBUG > 1:
            print "tried tok:", self.display()
        source.restore( ctx )
        return 0

    def display(self, level=0):
        name = self.parser.symbol_repr( self.codename )
        if self.value is None:
            return "<%s>" % name
        else:
            return "<%s>=='%s'" % (name, self.value)

    def match_token(self, builder, other):
        # Historical stuff.  Might be useful for debugging.
        if not isinstance(other, Token):
            raise RuntimeError("Unexpected token type")
        if other is self.parser.EmptyToken:
            return False
        res = other.isKeyword and other.codename == self.codename and self.value in [None, other.value]
        return res

    #def __eq__(self, other):
    #    XXX disabled to avoid strange differences between Python and RPython.
    #    XXX (moreover, only implementing __eq__ without __ne__ and __hash__
    #    XXX is a bit fragile)
    #    return self.codename == other.codename and self.value == other.value

    def eq(self, other):
        return self.codename == other.codename and self.value == other.value
        # XXX probably also "and self.isKeyword == other.isKeyword"

    def calc_first_set(self):
        """computes the list of possible next tokens
        """
        pass

    def validate( self, syntax_node ):
        """validate a syntax tree/subtree from this grammar node"""
        if self.codename != syntax_node.name:
            return False
        if self.value is None:
            return True
        if self.value == syntax_node.value:
            return True
        return False



class Parser(object):
    def __init__(self):
        pass
        _anoncount = self._anoncount = -10
        _count = self._count = 0
        self.sym_name = {}  # mapping symbol code -> symbol name
        self.symbols = {}   # mapping symbol name -> symbol code
        self.tokens = { 'NULLTOKEN' : -1 }
        self.EmptyToken = Token( self, -1, None )
        self.tok_name = {}
        self.tok_values = {}
        self.tok_rvalues = {}
        self._ann_sym_count = -10
        self._sym_count = 0
        self.all_rules = []
        self.root_rules = {}

    def symbol_repr( self, codename ):
        if codename in self.tok_name:
            return self.tok_name[codename]
        elif codename in self.sym_name:
            return self.sym_name[codename]
        return "%d" % codename

    def add_symbol( self, sym ):
        # assert isinstance( sym, str )
        if not sym in self.symbols:
            val = self._sym_count
            self._sym_count += 1
            self.symbols[sym] = val
            self.sym_name[val] = sym
            return val
        return self.symbols[ sym ]

    def add_anon_symbol( self, sym ):
        # assert isinstance( sym, str )
        if not sym in self.symbols:
            val = self._ann_sym_count
            self._ann_sym_count -= 1
            self.symbols[sym] = val
            self.sym_name[val] = sym
            return val
        return self.symbols[ sym ]

    def add_token( self, tok, value = None ):
        # assert isinstance( tok, str )
        if not tok in self.tokens:
            val = self._sym_count
            self._sym_count += 1
            self.tokens[tok] = val
            self.tok_name[val] = tok
            if value is not None:
                self.tok_values[value] = val
                # XXX : this reverse mapping seemed only to be used
                # because of pycodegen visitAugAssign
                self.tok_rvalues[val] = value
            return val
        return self.tokens[ tok ]

    def load_symbols( self, symbols ):
        for _value, _name in symbols.items():
            if _value < self._ann_sym_count:
                self._ann_sym_count = _value - 1
            if _value > self._sym_count:
                self._sym_count = _value + 1
            self.symbols[_name] = _value
            self.sym_name[_value] = _name

    def build_first_sets(self):
        """builds the real first tokens set for each rule in <rules>

        Because a rule can be recursive (directly or indirectly), the
        *simplest* algorithm to build each first set is to recompute them
        until Computation(N) = Computation(N-1), N being the number of rounds.
        As an example, on Python2.3's grammar, we need 19 cycles to compute
        full first sets.
        """
        rules = self.all_rules
        for r in rules:
            r.initialize_first_set()
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
        for r in rules:
            r.optimize_first_set()


    def build_alternative( self, name_id, args ):
        # assert isinstance( name_id, int )
        assert isinstance(args, list)
        alt = Alternative( self, name_id, args )
        self.all_rules.append( alt )
        return alt

    def Alternative_n(self, name, args ):
        # assert isinstance(name, str)
        name_id = self.add_symbol( name )
        return self.build_alternative( name_id, args )

    def build_sequence( self, name_id, args ):
        # assert isinstance( name_id, int )
        alt = Sequence( self, name_id, args )
        self.all_rules.append( alt )
        return alt

    def Sequence_n(self, name, args ):
        # assert isinstance(name, str)
        name_id = self.add_symbol( name )
        return self.build_sequence( name_id, args )

    def build_kleenestar( self, name_id, _min = 0, _max = -1, rule = None ):
        # assert isinstance( name_id, int )
        alt = KleeneStar( self, name_id, _min, _max, rule )
        self.all_rules.append( alt )
        return alt

    def KleeneStar_n(self, name, _min = 0, _max = -1, rule = None ):
        # assert isinstance(name, str)
        name_id = self.add_symbol( name )
        return self.build_kleenestar( name_id, _min, _max, rule )

    def Token_n(self, name, value = None ):
        # assert isinstance( name, str)
        # assert value is None or isinstance( value, str)
        name_id = self.add_token(name, value)
        return Token(self, name_id, value)

    # Debugging functions
    def show_rules(self, name):
        import re
        rex = re.compile(name)
        rules =[]
        for _name, _val in self.symbols.items():
            if rex.search(_name) and _val>=0:
                rules.append(self.root_rules[_val])
        return rules
