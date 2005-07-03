from pypy.interpreter.pyparser.grammar import Alternative, Sequence, KleenStar, \
     Token, EmptyToken, build_first_sets

class TestLookAheadBasics:

    def setup_method(self, method):
        self.tok1 = Token('t1', 'foo')
        self.tok2 = Token('t2', 'bar')
        self.tok3 = Token('t3', 'foobar')
        self.tokens = [self.tok1, self.tok2, self.tok3]
        build_first_sets(self.tokens)        

    def test_basic_token(self):
        assert self.tok1.first_set == [self.tok1]


    def test_basic_alternative(self):
        alt = Alternative('alt', self.tokens)
        build_first_sets([alt])
        assert alt.first_set == self.tokens


    def test_basic_sequence(self):
        seq = Sequence('seq', self.tokens)
        build_first_sets([seq])
        assert seq.first_set == [self.tokens[0]]

    def test_basic_kleenstar(self):
        tok1, tok2, tok3 = self.tokens
        kstar = KleenStar('kstar', 1, 3, tok1)
        build_first_sets([kstar])
        assert kstar.first_set == [tok1]
        kstar = KleenStar('kstar', 0, 3, tok1)
        build_first_sets([kstar])
        assert kstar.first_set == [tok1, EmptyToken]


    def test_maybe_empty_sequence(self):
        """S -> tok1{0,2} tok2{0,2}
         ==> S.first_set = [tok1, tok2, EmptyToken]
        """
        tok1, tok2, tok3 = self.tokens
        k1 = KleenStar('k1', 0, 2, tok1)
        k2 = KleenStar('k1', 0, 2, tok2)
        seq = Sequence('seq', [k1, k2])
        build_first_sets([k1, k2, seq])
        assert seq.first_set == [tok1, tok2, EmptyToken]


    def test_not_empty_sequence(self):
        """S -> tok1{0,2} tok2{1,2}
         ==> S.first_set = [tok1, tok2]
        """
        tok1, tok2, tok3 = self.tokens
        k1 = KleenStar('k1', 0, 2, tok1)
        k2 = KleenStar('k1', 1, 2, tok2)
        seq = Sequence('seq', [k1, k2])
        build_first_sets([k1, k2, seq])
        assert seq.first_set == [tok1, tok2]

def test_token_comparison():
    assert Token('t1', 'foo') == Token('t1', 'foo')
    assert Token('t1', 'foo') != Token('t2', 'foo')
    assert Token('t2', 'foo') != Token('t1', None)


class TestLookAhead:

     def setup_method(self, method):
         self.LOW = Token('LOW', 'low')
         self.CAP = Token('CAP' ,'cap')
         self.A = Alternative('A', [])
         k1 = KleenStar('k1', 0, rule=self.LOW)
         k2 = KleenStar('k2', 0, rule=self.CAP)
         self.B = Sequence('B', [k1, self.A])
         self.C = Sequence('C', [k2, self.A])
         self.A.args = [self.B, self.C]
         build_first_sets([self.A, self.B, self.C, self.LOW, self.CAP, k1, k2])
         
     def test_S_first_set(self):
         for s in  [Token('LOW', 'low'), EmptyToken, Token('CAP', 'cap')]:
             assert s in self.A.first_set
             assert s in self.B.first_set
             assert s in self.C.first_set
