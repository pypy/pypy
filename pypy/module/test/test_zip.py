import autopath

class AppTestZip:

   def test_zip_no_arguments(self):
      assert zip() ==  []
      assert zip(*[]) == []
   
   def test_one_list(self):
      assert zip([1, 2, 3]) == [(1,), (2,), (3,)]

   def test_three_lists_same_size(self):
      assert zip([1, 2, 3], [3, 4, 5], [6, 7, 8]) == (
                        [(1, 3, 6), (2, 4, 7), (3, 5, 8)])

   def test_three_lists_different_sizes(self):
      assert zip([1, 2], [3, 4, 5, 6], [6, 7, 8]) == (
                        [(1, 3, 6), (2, 4, 7)])

   def test_tuples(self):
      assert zip((1, 2, 3)) == [(1,), (2,), (3,)]

   def test_string(self):
      assert zip('hello') == [('h',), ('e',), ('l',), ('l',), ('o',)]

   def test_strings(self):
      assert zip('hello', 'bye') == (
                       [('h', 'b'), ('e', 'y'), ('l', 'e')])

   def test_mixed_types(self):
      assert zip('hello', [1,2,3,4], (7,8,9,10)) == (
                       [('h', 1, 7), ('e', 2, 8), ('l', 3, 9), ('l', 4, 10)])

   def test_from_cpython(self):
      from test.support_tests import TESTFN, unlink
      class BasicIterClass:
         def __init__(self, n):
            self.n = n
            self.i = 0
         def next(self):
            res = self.i
            if res >= self.n:
               raise StopIteration
            self.i = res + 1
            return res


      class IteratingSequenceClass:
         def __init__(self, n):
            self.n = n
         def __iter__(self):
            return BasicIterClass(self.n)

      class SequenceClass:
         def __init__(self, n):
            self.n = n
         def __getitem__(self, i):
            if 0 <= i < self.n:
               return i
            else:
               raise IndexError

      assert zip(*[(1, 2), 'ab']) == [(1, 'a'), (2, 'b')]

      raises(TypeError, zip, None)
      raises(TypeError, zip, range(10), 42)
      raises(TypeError, zip, range(10), zip)

      assert zip(IteratingSequenceClass(3)) == [(0,), (1,), (2,)]
      assert zip(SequenceClass(3)) == [(0,), (1,), (2,)]

      d = {"one": 1, "two": 2, "three": 3}
      assert d.items() ==  zip(d, d.itervalues())

      # Generate all ints starting at constructor arg.
      class IntsFrom:
         def __init__(self, start):
            self.i = start

         def __iter__(self):
            return self

         def next(self):
            i = self.i
            self.i = i+1
            return i

      f = open(TESTFN, "w")
      try:
         f.write("a\n" "bbb\n" "cc\n")
      finally:
         f.close()
      f = open(TESTFN, "r")
      try:
         assert (zip(IntsFrom(0), f, IntsFrom(-100)) ==
                          [(0, "a\n", -100),
                           (1, "bbb\n", -99),
                           (2, "cc\n", -98)])
      finally:
         f.close()
         try:
            unlink(TESTFN)
         except OSError:
            pass

      assert zip(xrange(5)) == [(i,) for i in range(5)]

      # Classes that lie about their lengths.
      class NoGuessLen5:
         def __getitem__(self, i):
            if i >= 5:
               raise IndexError
            return i

      class Guess3Len5(NoGuessLen5):
         def __len__(self):
            return 3

      class Guess30Len5(NoGuessLen5):
         def __len__(self):
            return 30

      assert len(Guess3Len5()) == 3
      assert len(Guess30Len5()) == 30
      assert zip(NoGuessLen5()) == zip(range(5))
      assert zip(Guess3Len5()) == zip(range(5))
      assert zip(Guess30Len5()) == zip(range(5))

      expected = [(i, i) for i in range(5)]
      for x in NoGuessLen5(), Guess3Len5(), Guess30Len5():
         for y in NoGuessLen5(), Guess3Len5(), Guess30Len5():
            assert zip(x, y) == expected

      
