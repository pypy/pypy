import unittest
from pypy.module.builtin import compile

class TestCompile(unittest.TestCase):
   """It makes basicaly not much sense, but we want to check,
      if there break something
   """

   def test_f(self):
      codeobject = compile("def main(): return None", '?', 'exec')
      self.assertEquals(codeobject.co_names[0], 'main')

if __name__ == '__main__':
    unittest.main()
 
