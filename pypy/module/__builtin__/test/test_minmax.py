import autopath

class AppTestMin:

   def test_min_notseq(self):
      raises(TypeError, min, 1)

   def test_min_usual(self):
      assert min(1, 2, 3) == 1

   def test_min_floats(self):
      assert min(0.1, 2.7, 14.7) == 0.1

   def test_min_chars(self):
      assert min('a', 'b', 'c') == 'a'

   def test_min_strings(self):
      assert min('aaa', 'bbb', 'c') == 'aaa'

   def test_min_mixed(self):
      assert min('1', 2, 3, 'aa') == 2

   def test_min_noargs(self):
      raises(TypeError, min)

   def test_min_empty(self):
      raises(ValueError, min, [])

class AppTestMax:

   def test_max_notseq(self):
      raises(TypeError, max, 1)

   def test_max_usual(self):
      assert max(1, 2, 3) == 3

   def test_max_floats(self):
      assert max(0.1, 2.7, 14.7) == 14.7

   def test_max_chars(self):
      assert max('a', 'b', 'c') == 'c'

   def test_max_strings(self):
      assert max('aaa', 'bbb', 'c') == 'c'

   def test_max_mixed(self):
      assert max('1', 2, 3, 'aa') == 'aa'

   def test_max_noargs(self):
      raises(TypeError, max)

   def test_max_empty(self):
      raises(ValueError, max, [])
