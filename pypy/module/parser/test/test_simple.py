import unittest, inspect, compiler
import sys
import parser as cpy_parser
sys.path.insert(0, '..')
del sys.modules['parser']
import pyparser as parser
assert hasattr(parser, 'PyTokenizer'), "not using Basil's common parser" 

class SimpleParserTestCase(unittest.TestCase):
    def test_compile_empty_function(self):
        ast1 = parser.suite('def f(): pass')
        ast2 = cpy_parser.suite('def f(): pass')
    
        tup1 = parser.ast2tuple(ast1)
        tup2 = cpy_parser.ast2tuple(ast2)

        self.assertEquals(tup1, tup2)

    def test_compile_function(self):
        source = "def f(x, arg1=None): return x"
        ast1 = parser.suite(source)
        ast2 = cpy_parser.suite(source)
    
        tup1 = parser.ast2tuple(ast1)
        tup2 = cpy_parser.ast2tuple(ast2)

        self.assertEquals(tup1, tup2)

class SimpleCompilerTestCase(unittest.TestCase):
    def test_compile_simple(self):
        source = "def f(arg): return arg + 1\ni = f(41)"
        co1, co2 = self.compile2(source)
        d1, d2 = {}, {} 
        exec co1 in d1
        exec co2 in d2
        self.assertEquals(d1['i'], d2['i'])

    def compile2(self, source):
        #ast1 = cpy_parser.suite(source)
        #ast2 = parser.suite(source)
        #tup1 = cpy_parser.ast2tuple(ast1, 1)
        #tup2 = parser.ast2tuple(ast2, 1)
        #self.assertEquals(tup1, tup2)

        #print "cpython compile", source
        compiler.transformer.parser = cpy_parser
        co1 = compiler.compile(source, '', 'exec')

        #print "python compile", source
        compiler.transformer.parser = parser
        co2 = compiler.compile(source, '', 'exec')

        return co1, co2

if __name__ == '__main__':
    unittest.main()
