from grammar import Token, GrammarProxy
from grammar import AbstractBuilder, AbstractContext


ORDA = ord("A")
ORDZ = ord("Z")
ORDa = ord("a")
ORDz = ord("z")
ORD0 = ord("0")
ORD9 = ord("9")
ORD_ = ord("_")

def is_py_name( name ):
    if len(name)<1:
        return False
    v = ord(name[0])
    if not (ORDA <= v <= ORDZ or
            ORDa <= v <= ORDz or v == ORD_):
        return False
    for c in name:
        v = ord(c)
        if not (ORDA <= v <= ORDZ or
                ORDa <= v <= ORDz or
                ORD0 <= v <= ORD9 or
                v == ORD_):
            return False
    return True


class NameToken(Token):
    """A token that is not a keyword"""
    isKeyword = False

    def __init__(self, parser):
        Token.__init__(self, parser, parser.tokens['NAME'])

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
            # XXX (adim): this is trunk's keyword management
            # if tk.value not in builder.keywords:
            if not tk.isKeyword:
                ret = builder.token( tk.codename, tk.value, source )
                return ret
        source.restore( ctx )
        return 0


    def match_token(self, builder, other):
        # Historical stuff.  Might be useful for debugging.
        if not isinstance(other, Token):
            raise RuntimeError("Unexpected token type")
        if other is self.parser.EmptyToken:
            return False
        if other.codename != self.codename:
            return False
        # XXX (adim): this is trunk's keyword management
        # if other.value in builder.keywords:
        if other.isKeyword:
            return False
        return True


class EBNFBuilderContext(AbstractContext):
    def __init__(self, stackpos, seqcounts, altcounts):
        self.stackpos = stackpos
        self.seqcounts = seqcounts
        self.altcounts = altcounts


class EBNFBuilder(AbstractBuilder):
    """Build a grammar tree"""
    def __init__(self, gram_parser, dest_parser):
        AbstractBuilder.__init__(self, dest_parser)
        self.gram = gram_parser
        self.rule_stack = []
        self.seqcounts = [] # number of items in the current sequence
        self.altcounts = [] # number of sequence in the current alternative
        self.curaltcount = 0
        self.curseqcount = 0
        self.current_subrule = 0
        self.current_rule = -1
        self.current_rule_name = ""
        self.tokens = {}
        self.keywords = []
        NAME = dest_parser.add_token('NAME')
        # NAME = dest_parser.tokens['NAME']
        self.tokens[NAME] = NameToken(dest_parser)

    def context(self):
        return EBNFBuilderContext(len(self.rule_stack), self.seqcounts, self.altcounts)

    def restore(self, ctx):
        del self.rule_stack[ctx.stackpos:]
        self.seqcounts = ctx.seqcounts
        self.altcounts = ctx.altcounts

    def new_symbol(self):
        """Allocate and return a new (anonymous) grammar symbol whose
        name is based on the current grammar rule being parsed"""
        rule_name = ":" + self.current_rule_name + "_%d" % self.current_subrule
        self.current_subrule += 1
        name_id = self.parser.add_anon_symbol( rule_name )
        return name_id

    def new_rule(self, rule):
        """A simple helper method that registers a new rule as 'known'"""
        self.parser.all_rules.append(rule)
        return rule

    def resolve_rules(self):
        """Remove GrammarProxy objects"""
        to_be_deleted = {}
        for rule in self.parser.all_rules:
            # for i, arg in enumerate(rule.args):
            for i in range(len(rule.args)):
                arg = rule.args[i]
                if isinstance(arg, GrammarProxy):
                    real_rule = self.parser.root_rules[arg.codename]
                    if isinstance(real_rule, GrammarProxy):
                        # If we still have a GrammarProxy associated to this codename
                        # this means we have encountered a terminal symbol
                        to_be_deleted[ arg.codename ] = True
                        rule.args[i] = self.get_token( arg.codename )
                        #print arg, "-> Token(",arg.rule_name,")" 
                    else:
                        #print arg, "->", real_rule
                        rule.args[i] = real_rule
        for codename in to_be_deleted.keys():
            del self.parser.root_rules[codename]

    def get_token(self, codename ):
        """Returns a new or existing Token"""
        if codename in self.tokens:
            return self.tokens[codename]
        token = self.tokens[codename] = Token(self.parser, codename, None)
        return token

    def get_symbolcode(self, name):
        return self.parser.add_symbol( name )

    def get_rule( self, name ):
        if name in self.parser.tokens:
            codename = self.parser.tokens[name]
            return self.get_token( codename )
        codename = self.get_symbolcode( name )
        if codename in self.parser.root_rules:
            return self.parser.root_rules[codename]
        proxy = GrammarProxy( self.parser, name, codename )
        self.parser.root_rules[codename] = proxy
        return proxy

    def alternative(self, rule, source):
        return True

    def pop_rules( self, count ):
        offset = len(self.rule_stack)-count
        assert offset>=0
        rules = self.rule_stack[offset:]
        del self.rule_stack[offset:]
        return rules

    def sequence(self, rule, source, elts_number):
        _rule = rule.codename
        if _rule == self.gram.sequence:
            if self.curseqcount==1:
                self.curseqcount = 0
                self.curaltcount += 1
                return True
            rules = self.pop_rules(self.curseqcount)
            new_rule = self.parser.build_sequence( self.new_symbol(), rules )
            self.rule_stack.append( new_rule )
            self.curseqcount = 0
            self.curaltcount += 1
        elif _rule == self.gram.alternative:
            if self.curaltcount == 1:
                self.curaltcount = 0
                return True
            rules = self.pop_rules(self.curaltcount)
            new_rule = self.parser.build_alternative( self.new_symbol(), rules )
            self.rule_stack.append( new_rule )
            self.curaltcount = 0
        elif _rule == self.gram.group:
            self.curseqcount += 1
        elif _rule == self.gram.option:
            # pops the last alternative
            rules = self.pop_rules( 1 )
            new_rule = self.parser.build_kleenestar( self.new_symbol(), _min=0, _max=1, rule=rules[0] )
            self.rule_stack.append( new_rule )
            self.curseqcount += 1
        elif _rule == self.gram.rule:
            assert len(self.rule_stack)==1
            old_rule = self.rule_stack[0]
            del self.rule_stack[0]
            if isinstance(old_rule,Token):
                # Wrap a token into an alternative
                old_rule = self.parser.build_alternative( self.current_rule, [old_rule] )
            else:
                # Make sure we use the codename from the named rule
                old_rule.codename = self.current_rule
            self.parser.root_rules[self.current_rule] = old_rule
            self.current_subrule = 0
        return True

    def token(self, name, value, source):
        if name == self.gram.TOK_STRING:
            self.handle_TOK_STRING( name, value )
            self.curseqcount += 1
        elif name == self.gram.TOK_SYMDEF:
            self.current_rule = self.get_symbolcode( value )
            self.current_rule_name = value
        elif name == self.gram.TOK_SYMBOL:
            rule = self.get_rule( value )
            self.rule_stack.append( rule )
            self.curseqcount += 1
        elif name == self.gram.TOK_STAR:
            top = self.rule_stack[-1]
            rule = self.parser.build_kleenestar( self.new_symbol(), _min=0, rule=top)
            self.rule_stack[-1] = rule
        elif name == self.gram.TOK_ADD:
            top = self.rule_stack[-1]
            rule = self.parser.build_kleenestar( self.new_symbol(), _min=1, rule=top)
            self.rule_stack[-1] = rule
        elif name == self.gram.TOK_BAR:
            assert self.curseqcount == 0
        elif name == self.gram.TOK_LPAR:
            self.altcounts.append( self.curaltcount )
            self.seqcounts.append( self.curseqcount )
            self.curseqcount = 0
            self.curaltcount = 0
        elif name == self.gram.TOK_RPAR:
            assert self.curaltcount == 0
            self.curaltcount = self.altcounts.pop()
            self.curseqcount = self.seqcounts.pop()
        elif name == self.gram.TOK_LBRACKET:
            self.altcounts.append( self.curaltcount )
            self.seqcounts.append( self.curseqcount )
            self.curseqcount = 0
            self.curaltcount = 0
        elif name == self.gram.TOK_RBRACKET:
            assert self.curaltcount == 0
            assert self.curseqcount == 0
            self.curaltcount = self.altcounts.pop()
            self.curseqcount = self.seqcounts.pop()
        return True

    def handle_TOK_STRING( self, name, value ):
        if value in self.parser.tok_values:
            # punctuation
            tokencode = self.parser.tok_values[value]
            tok = Token(self.parser, tokencode, None)
        else:
            if not is_py_name(value):
                raise RuntimeError("Unknown STRING value ('%s')" % value)
            # assume a keyword
            tok = Token(self.parser, self.parser.tokens['NAME'], value)
            if value not in self.keywords:
                self.keywords.append(value)
        self.rule_stack.append(tok)

