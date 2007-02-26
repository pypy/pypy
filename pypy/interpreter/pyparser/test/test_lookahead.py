from pypy.interpreter.pyparser.grammar import Alternative, Sequence, KleeneStar, \
     Token, Parser

class TestLookAheadBasics:

    def setup_method(self, method):
        self.parser = Parser()
        self.tok1 = self.parser.Token_n("t1", 'foo')
        self.tok2 = self.parser.Token_n("t2", 'bar')
        self.tok3 = self.parser.Token_n("t3", 'foobar')
        self.tokens = [self.tok1, self.tok2, self.tok3]
        self.parser.build_first_sets()        

    def test_basic_token(self):
        assert self.tok1.first_set == [self.tok1]

    def test_basic_alternative(self):
        alt = self.parser.Alternative_n("a1t", self.tokens)
        self.parser.build_first_sets()
        assert alt.first_set == self.tokens


    def test_basic_sequence(self):
        seq = self.parser.Sequence_n("seq", self.tokens)
        self.parser.build_first_sets()
        assert seq.first_set == [self.tokens[0]]

    def test_basic_kleenstar(self):
        tok1, tok2, tok3 = self.tokens
        kstar1 = self.parser.KleeneStar_n("k", 1, 3, tok1)
        kstar2 = self.parser.KleeneStar_n("k2", 0, 3, tok1)
        self.parser.build_first_sets()
        assert kstar1.first_set == [tok1]
        assert kstar2.first_set == [tok1, self.parser.EmptyToken]


    def test_maybe_empty_sequence(self):
        """S -> tok1{0,2} tok2{0,2}
         ==> S.first_set = [tok1, tok2, EmptyToken]
        """
        tok1, tok2, tok3 = self.tokens
        k1 = self.parser.KleeneStar_n( "k1", 0, 2, tok1)
        k2 = self.parser.KleeneStar_n("k2", 0, 2, tok2)
        seq = self.parser.Sequence_n( "seq", [k1, k2])
        self.parser.build_first_sets()
        assert seq.first_set == [tok1, tok2, self.parser.EmptyToken]


    def test_not_empty_sequence(self):
        """S -> tok1{0,2} tok2{1,2}
         ==> S.first_set = [tok1, tok2]
        """
        tok1, tok2, tok3 = self.tokens
        k1 = self.parser.KleeneStar_n("k1", 0, 2, tok1)
        k2 = self.parser.KleeneStar_n("k2", 1, 2, tok2)
        seq = self.parser.Sequence_n("seq", [k1, k2])
        self.parser.build_first_sets()
        assert seq.first_set == [tok1, tok2]

    def test_token_comparison(self):
        tok1  = self.parser.Token_n( "tok1", "foo" )
        tok1b = self.parser.Token_n( "tok1", "foo" )
        tok2  = self.parser.Token_n( "tok2", "foo" )
        tok3  = self.parser.Token_n( "tok2", None )
        assert tok1 == tok1b
        assert tok1 != tok2
        assert tok2 != tok3



class TestLookAhead:

     def setup_method(self, method):
         p = self.parser = Parser()
         self.LOW = p.Token_n( 'LOW', 'low')
         self.CAP = p.Token_n( 'CAP' ,'cap')
         self.A = p.Alternative_n( 'R_A', [])
         k1 = p.KleeneStar_n( 'R_k1', 0, rule=self.LOW)
         k2 = p.KleeneStar_n( 'R_k2', 0, rule=self.CAP)
         self.B = p.Sequence_n( 'R_B', [k1, self.A])
         self.C = p.Sequence_n( 'R_C', [k2, self.A])
         self.A.args = [self.B, self.C]
         p.build_first_sets()
         
     def test_S_first_set(self):
         p = self.parser
         LOW = p.tokens['LOW']
         CAP = p.tokens['CAP']
         for s in  [Token(p, LOW, 'low'), p.EmptyToken, Token(p, CAP, 'cap')]:
             assert s in self.A.first_set
             assert s in self.B.first_set
             assert s in self.C.first_set
