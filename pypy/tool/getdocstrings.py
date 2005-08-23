import autopath
import re
from os import listdir

where = autopath.pypydir + '/objspace/std/'
quote = '(' + "'" + '|' + '"' + ')'
triplequotes = '(' + "'''" + '|' + '"""' + ')'
# Note: this will produce erroneous result if you nest triple quotes
# in your docstring.

def mk_std_filelist():
    ''' go to pypy/objs/std and get all the *type.py files '''
    filelist = []
    filenames = listdir(where)
    for f in filenames:
        if f.endswith('type.py'):
            filelist.append(f)
    return filelist


def compile_doc():
    return re.compile(r"__doc__\s+=\s+" + triplequotes +
                      r"(?P<docstring>.*)"+ triplequotes ,
                      re.DOTALL
                      )

def compile_typedef(match):
    return re.compile(r"(?P<whitespace>\s+)"
                      + r"(?P<typeassign>" + match
                      + "_typedef = StdTypeDef+\s*\(\s*"
                      + quote + match +  quote + ",).*"
                      + r"(?P<indent>^\s+)"
                      + r"(?P<newassign>__new__\s*=\s*newmethod)",
                      re.DOTALL | re.MULTILINE)

def get_pypydoc(match, sourcefile):
    doc = compile_doc()
    
    try: # if this works we already have a docstring
        pypydoc = doc.search(sourcefile).group('docstring')

    except AttributeError: # No pypy docstring
        return None

    return pypydoc

def sub_pypydoc(match, sourcefile, cpydoc):
    try:
        typedef = compile_typedef(match)
        tdsearch = typedef.search(sourcefile).group('typeassign')
        newsearch = typedef.search(sourcefile).group('newassign')
        if not tdsearch:
            print 'tdsearch, not found', match
        if not newsearch:
            print 'newsearch, not found', match
    except AttributeError:
        pass # so stringtype does not blow up.
    return None

def get_cpydoc(match):
    try:
        cpydoc = eval(match + '.__doc__')

    except NameError: # No CPython docstring
        cpydoc = None
    return cpydoc

if __name__ == '__main__':

    #filenames = mk_std_filelist()
    #filenames = ['basestringtype.py']
    filenames = ['tupletype.py']

    docstrings = []

    for f in filenames:
        match = f[:-7]
        sourcefile = file(where + f).read()
        
        pypydoc = get_pypydoc(match, sourcefile)
        cpydoc = get_cpydoc(match)

        if pypydoc:
            print match, 'already has a pypydoc'
        elif not cpydoc:
            print match, 'does not have a cpydoc'

        else:
            print match, 'has cpydoc.   Trying to insert'
            docstring="__doc__ = '''" + cpydoc + "'''"

            typedef = compile_typedef(match)
            
            try:
                newsearch = typedef.search(sourcefile)
                if newsearch:
                    print match, '__new__ found'
                    print newsearch.groupdict()
                    print newsearch.group('newassign')
                    print re.sub(newsearch.group('indent') +
                                 newsearch.group('newassign'),
                                 newsearch.group('indent') +
                                 docstring + '\n' +
                                 newsearch.group('indent') +
                                 newsearch.group('newassign'),
                                 sourcefile)

            except AttributeError:
                print match, 'no __new__ found'
                
            
