import autopath
from os import listdir
import py, re

this_dir = autopath.this_dir
pypy_dir = autopath.pypydir
# Naming weirdness: why not both pypy_dir and this_dir or pypydir and thisdir

from pypy.tool.getdocstrings import quote, triplequotes
from pypy.tool.getdocstrings import mk_std_filelist

class TestDocStringInserter:
    def setup_method(self, method):
        self.fd1 = file(this_dir+'/fordocstrings1', 'r')
 
    def teardown_method(self, method):
        self.fd1.close()

    def test_mkfilelist(self):
        assert mk_std_filelist() == [
            'basestringtype.py', 'unicodetype.py', 'inttype.py',
            'nonetype.py', 'longtype.py', 'slicetype.py',
            'itertype.py', 'floattype.py', 'typetype.py',
            'dicttype.py', 'dictproxytype.py', 'tupletype.py',
            'booltype.py', 'objecttype.py', 'stringtype.py',
            'listtype.py']

    def test_gottestfile(self):
        s = self.fd1.read()       # whole file as string

        s1 = 'from pypy.objspace.std.stdtypedef import *\n\n\n# ____________________________________________________________\n\nbasestring_typedef = StdTypeDef("basestring",\n    )\n'
        
        assert s == s1


    def test_compile_typedef(self):
        match = 'basestring'
        s = self.fd1.read()
        
        typedef = re.compile(r"(?P<whitespace>\s*)"
                            + r"(?P<typeassign>" + match
                            + "_typedef = StdTypeDef+\s*\(\s*"
                            + quote + match +  quote + ",)",
                            re.DOTALL
                             )
        
        print s
        tdsearch = typedef.search(s).group('typeassign')
        
        assert tdsearch
                 
        
        
        

        
