from pypy.interpreter.pyparser.grammar import Alternative, Sequence, KleenStar, \
     Token, EmptyToken, build_first_sets

class TestLookAheadBasics:

    def setup_method(self, method):
        self.count = 0
        self.tok1 = Token(self.nextid(), 'foo')
        self.tok2 = Token(self.nextid(), 'bar')
        self.tok3 = Token(self.nextid(), 'foobar')
        self.tokens = [self.tok1, self.tok2, self.tok3]
        build_first_sets(self.tokens)        

    def nextid(self):
        self.count+=1
        return self.count

    def test_basic_token(self):
        assert self.tok1.first_set == [self.tok1]


    def test_basic_alternative(self):
        alt = Alternative(self.nextid(), self.tokens)
        build_first_sets([alt])
        assert alt.first_set == self.tokens


    def test_basic_sequence(self):
        seq = Sequence(self.nextid(), self.tokens)
        build_first_sets([seq])
        assert seq.first_set == [self.tokens[0]]

    def test_basic_kleenstar(self):
        tok1, tok2, tok3 = self.tokens
        kstar = KleenStar(self.nextid(), 1, 3, tok1)
        build_first_sets([kstar])
        assert kstar.first_set == [tok1]
        kstar = KleenStar(self.nextid(), 0, 3, tok1)
        build_first_sets([kstar])
        assert kstar.first_set == [tok1, EmptyToken]


    def test_maybe_empty_sequence(self):
        """S -> tok1{0,2} tok2{0,2}
         ==> S.first_set = [tok1, tok2, EmptyToken]
        """
        tok1, tok2, tok3 = self.tokens
        k1 = KleenStar(self.nextid(), 0, 2, tok1)
        k2 = KleenStar(self.nextid(), 0, 2, tok2)
        seq = Sequence(self.nextid(), [k1, k2])
        build_first_sets([k1, k2, seq])
        assert seq.first_set == [tok1, tok2, EmptyToken]


    def test_not_empty_sequence(self):
        """S -> tok1{0,2} tok2{1,2}
         ==> S.first_set = [tok1, tok2]
        """
        tok1, tok2, tok3 = self.tokens
        k1 = KleenStar(self.nextid(), 0, 2, tok1)
        k2 = KleenStar(self.nextid(), 1, 2, tok2)
        seq = Sequence(self.nextid(), [k1, k2])
        build_first_sets([k1, k2, seq])
        assert seq.first_set == [tok1, tok2]

def test_token_comparison():
    assert Token(1, 'foo') == Token(1, 'foo')
    assert Token(1, 'foo') != Token(2, 'foo')
    assert Token(2, 'foo') != Token(2, None)


LOW = 1
CAP = 2
R_A = 3
R_B = 4
R_C = 5
R_k1 = 6
R_k2 = 7

class TestLookAhead:

     def setup_method(self, method):
         self.LOW = Token(LOW, 'low')
         self.CAP = Token(CAP ,'cap')
         self.A = Alternative(R_A, [])
         k1 = KleenStar(R_k1, 0, rule=self.LOW)
         k2 = KleenStar(R_k2, 0, rule=self.CAP)
         self.B = Sequence(R_B, [k1, self.A])
         self.C = Sequence(R_C, [k2, self.A])
         self.A.args = [self.B, self.C]
         build_first_sets([self.A, self.B, self.C, self.LOW, self.CAP, k1, k2])
         
     def test_S_first_set(self):
         for s in  [Token(LOW, 'low'), EmptyToken, Token(CAP, 'cap')]:
             assert s in self.A.first_set
             assert s in self.B.first_set
             assert s in self.C.first_set
