#! /usr/bin/env python
# ______________________________________________________________________
import unittest, inspect, compiler
import sys

# XXX - Is there a better way to detect that we are in PyPy?
print sys.version
if "pypy" in sys.version:
    cpy_parser = None
    import parser
else:
    import parser as cpy_parser
    del sys.modules['parser']
    import pypy.module.parser.pyparser as parser
    print dir(parser)
    #assert hasattr(parser, 'PyTokenizer'), "not using Basil's common parser"
    from pypy.objspace.std import StdObjSpace
    space = StdObjSpace()
    # XXX - This is a hack to get around the object space.  Should take a
    # closer look at these tests and build real PyPy tests, not hacked
    # CPython-style tests.  One might also note this is an application level
    # test of interpreter level code, unless it is run in the mode given above.
    old_suite = parser.suite
    def new_suite (source):
        return old_suite(space, source)
    parser.suite = new_suite

class SimpleParserTestCase(unittest.TestCase):
    def test_compile_empty_function(self):
        source = "def f(): pass"

        if cpy_parser != None:
            ast1 = parser.suite(source)
            tup1 = ast1.totuple()
            ast2 = cpy_parser.suite(source)
            tup2 = cpy_parser.ast2tuple(ast2)
        else:
            ast1 = parser.suite(source)
            tup1 = parser.ast2tuple(ast1)
            # XXX - This is hand computed against the 2.3.5 parser!
            tup2 = (257,
                    (264,
                     (285,
                      (259,
                       (1, 'def'),
                       (1, 'f'),
                       (260,
                        (7, '('),
                        (8, ')')),
                       (11, ':'),
                       (291,
                        (265,
                         (266,
                          (271,
                           (1, 'pass'))),
                         (4, '')))))),
                    (0, ''))

        self.assertEquals(tup1, tup2)

    def test_compile_function(self):
        source = "def f(x, arg1=None): return x"
        if cpy_parser != None:
            ast1 = parser.suite(source)
            tup1 = parser.ast2tuple(ast1)
            ast2 = cpy_parser.suite(source)
            tup2 = cpy_parser.ast2tuple(ast2)
        else:
            # XXX - This is hand computed against the 2.3.5 parser!
            ast1 = parser.suite(source)
            tup1 = parser.ast2tuple(ast1)
            tup2 = (257,
                    (264,
                     (285,
                      (259,
                       (1, 'def'),
                       (1, 'f'),
                       (260, (7, '('),
                        (261,
                         (262, (1, 'x')), (12, ','),
                         (262, (1, 'arg1')), (22, '='),
                         (292,
                          (293,
                           (294,
                            (295,
                             (297,
                              (298,
                               (299,
                                (300,
                                 (301,
                                  (302,
                                   (303, (304, (305, (1, 'None'))))))))))))))),
                        (8, ')')),
                       (11, ':'),
                       (291,
                        (265,
                         (266,
                          (272,
                           (275, (1, 'return'),
                            (313,
                             (292,
                              (293,
                               (294,
                                (295,
                                 (297,
                                  (298,
                                   (299,
                                    (300,
                                     (301,
                                      (302,
                                       (303,
                                        (304, (305, (1, 'x')))))))))))))))))),
                         (4, '')))))), (0, ''))
        self.assertEquals(tup1, tup2)

class SimpleCompilerTestCase(unittest.TestCase):
    def test_compile_simple(self):
        source = "def f(arg): return arg + 1\ni = f(41)"
        co1, co2 = self.compile2(source)
        d1, d2 = {}, {}
        exec co2 in d2
        if co1 != None:
            exec co1 in d1
            self.assertEquals(d1['i'], d2['i'])
        else:
            self.assertEquals(d2['i'], 42)

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
