import autopath
import difflib

leadincode = """
import sys

class PseudoOut:
    def __init__(self):
        self.out = []
    def flush(self):
        pass
    def write(self, item):
        self.out.append(str(item))
    def writelines(self, items):
        for item in items:
            self.out.append(str(item))
    def getoutput(self):
        '''Not part of the output stream interface.'''
        return ''.join(self.out)

out = PseudoOut()

oldout, sys.stdout = sys.stdout, out
olderr, sys.stderr = sys.stderr, out
"""

cleanupcode = """
sys.stdout = oldout
sys.stderr = olderr

retval = out.getoutput()
"""

def runcode(space, source, filename, w_glob):
    w = space.wrap
    w_compile = space.getitem(space.builtin.w_dict, w('compile'))
    w_code = space.call_function(w_compile, w(source), w(filename), w('exec'))
    pycode = space.unwrap(w_code)
    pycode.exec_code(space, w_glob, w_glob)
    
def getoutput(space, source, filename):
    w_bookendglobals = space.newdict([])
    runcode(space, leadincode, '<str>', w_bookendglobals)
    w_scratchglobals = space.newdict([])
    runcode(space, source, filename, w_scratchglobals)
    runcode(space, cleanupcode, '<str>', w_bookendglobals)
    #Get 'retval' from the bookendglobals - contains output
    return space.unwrap(space.getitem(w_bookendglobals, space.wrap('retval')))

def getsection(linelist, section_name = None, savelineno = False):
    #Strips out all '##!' line delimiters.
    #If section_name is None, return just the leadin code.
    #If section_name is not present in the linelist, raise an error.
    #If savelineno is true, add fake lines to keep the absolute line
    #   numbers the same as in the original file.
    
    #Leadin code is run by all sections
    save = True
    seen = False
    accumulator = []
    for line in linelist:
        if line[:3] == '##!':
            if line[3:].strip() == section_name or section_name is None:
                save = True
                seen = True
            else:
                save = False
            if savelineno:
                accumulator.append('\n')
        elif save:
            accumulator.append(line)
        elif savelineno:
            accumulator.append('\n')
    if not seen:
        raise KeyError('Section "'+section_name+'" not found in file.')
    return accumulator
            
def compare(space, filename, section = None):
    """Compare an application level script to expected output.

    The output of 'filename' when run at application level as a script
    is compared to the appropriate '.txt' file (e.g. test.py -> test.txt).
    If no difference is seen, the function returns an empty string (False).
    If a difference is seen, the diffenrence in the form of a unified diff is
    returned as a multiline string (True).

    The optional section argument allows selective execution of portions of
    the code. It looks for blocks delimited by '##! <section_name>' lines,
    where <section_name> is the string passed to the section argument. None
    executes the entire script. The output file should also be delimited by
    the same section markers.
    """
    f = file(filename, 'r')
    try:
        sourcelines = f.readlines()
    finally:
        f.close()
    source = ''.join(getsection(sourcelines, section, savelineno = True))
    output = getoutput(space, source, filename).splitlines(True)

    outfilename = '.'.join(filename.split('.')[:-1]+['txt'])
    try:
        f = file(outfilename, 'r')
        try:
            outfilelines = f.readlines()
        finally:
            f.close()
    except KeyboardInterrupt:
        pass
    except:
        #If there are problems loading outfile, assume null output
        outfilelines = ['']
        
    outfile = getsection(outfilelines, section)
    if not outfile and not output: #Catch degenerate case where both are empty
        return ''
    diff = list(difflib.unified_diff(outfile, output,
                                     fromfile=outfilename, tofile=filename))

    if diff:
        return ''.join(diff)
    else:
        return ''
