import unittest
from pypy.module.builtin import compile as compile

class TestCompile(unittest.TestCase):
   """It makes basicaly not much sense, but we want to check,
      if there break something
   """

   def test_f(self):
      testcode = """
def main():
    aStr = 'hello world'
    print len(aStr)
                 """
      codeobject = compile(testcode, '?', 'exec')
      print codeobject
      self.assertEquals(codeobject.co_name, 'main')





if __name__ == '__main__':
    unittest.main()
 
