import autopath
from pypy.module.builtin_app import map
from pypy.tool import test

# trivial objects for testing 

class TrivialObject:

   def __init__(self):
      self.s1 = 'I am a string'

   def do_something(self):
      self.s1 = "Now I am another string"

t = TrivialObject()
t1 = TrivialObject()
t1.do_something()

class TestVars(test.TestCase):

   def test_vars_no_arguments(self):
      self.assertEqual(vars(), locals())

   def test_vars_too_many_arguments(self):
      self.assertRaises(TypeError, vars,  t, t1)

   def test_vars_correct_arguments(self):
      self.assertEqual(vars(t), t.__dict__)
      self.assertEqual(vars(t1), t1.__dict__)
      self.assertNotEqual(vars(t1), t.__dict__)
      
if __name__ == '__main__':
    test.main()


