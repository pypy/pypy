import autopath
import re
from os import listdir

where = autopath.pypydir + '/objspace/std/'
triplequotes = '(' + "'''" + '|' + '"""' + ')'
quote = '(' + "'" + '|' + '"' + ')'
doc = re.compile(r"__doc__\s+=\s+" + triplequotes +
                 r"(?P<docstring>.*)"+ triplequotes ,
                 re.DOTALL
                 )

def mk_std_filelist():
    ''' go to pypy/objs/std and get all the *type.py files '''
    filelist = []
    filenames = listdir(where)
    for f in filenames:
        if f.endswith('type.py'):
            filelist.append(f)
    return filelist

def mk_typelist(filelist):
    ''' generate a list of the types we expect to find in our files'''
    return [f[:-7] for f in filelist]

def compile_doc():
    return re.compile(r"__doc__\s+=\s+" + triplequotes +
                      r"(?P<docstring>.*)"+ triplequotes ,
                      re.DOTALL
                      )

def compile_typedef(match):
    return re.compile(r"(?P<whitespace>\s*)"
                      + r"(?P<typeassign>" + match
                      + "_typedef = StdTypeDef+\s*\(\s*"
                      + quote + match +  quote + ",)",
                      re.DOTALL
                      )

def compile_typedef_match(matchstring, sourcefile):
    return re.compile(r"(?P<whitespace>\s+)"
                      + r"(?P<typeassign>" + matchstring
                      + "_typedef = StdTypeDef+\s*\(\s*"
                      + quote + matchstring +  quote + ",)"
                      + r"(?P<indent>.*\s+)"
                      + r"(?P<newassign>__new__)",
                      re.DOTALL
                      ).match(sourcefile).span()

if __name__ == '__main__':

    filenames = listdir(where)

    docstrings = []

    for f in filenames:
        if f.endswith('type.py'):
            match = f[:-7]
            s = match + '.__doc__'

            try:
                cpydoc = eval(match + '.__doc__')
                #cpydoc = 'cpy_stuff'
            except NameError: # No CPython docstring
                cpydoc = None

            sourcefile = file(where + f).read()


            # will produce erroneous result if you nest triple quotes
            # in your docstring.  
            
            doc = re.compile(r"__doc__\s+=\s+" + triplequotes +
                             r"(?P<docstring>.*)"+ triplequotes ,
                             re.DOTALL
                             )
            typedef = re.compile(r"(?P<whitespace>\s+)"
                                 + r"(?P<typeassign>" + match
                                 + "_typedef = StdTypeDef+\s*\(\s*"
                                 + quote + match +  quote + ",)"
                                 + r"(?P<indent>.*\s+)"
                                 + r"(?P<newassign>__new__)",
                                 re.DOTALL)

            try:
                pypydoc = doc.search(sourcefile).group('docstring')
                #pypydoc = 'pypy_stuff'
            except AttributeError: # No pypy docstring
                pypydoc = None
                tdsearch = None
                try:
                    tdsearch = typedef.search(sourcefile).group('typeassign')
                    newsearch = typedef.search(sourcefile).group('newassign')
                    if tdsearch:
                        print tdsearch, ' found', match
                        print newsearch
                    else:
                        print tdsearch, ' not found', match

                except AttributeError:
                    pass # so stringtype does not blow up.

            docstrings.append((match, cpydoc, pypydoc))

    for (m, c, p) in docstrings:
        if p:
            print m, 'already has a pypydoc'
        elif not c:  
            print m, 'does not have a cpydoc'
        elif not tdsearch:
            print m, 'has cpydoc but no ..._typedef = StdTypeDef.  Skipping'
        else:
            print m, 'has cpydoc and ..._typedef = StdTypeDef.  Inserting'


            


    
