
class Source(object):
    """ a mutable object holding a source code fragment, 
        automatically deindenting it. 
    """
    def __init__(self, *parts): 
        self.lines = lines = []
        for part in parts:
            if isinstance(part, Source):
                lines.extend(part.lines) 
            else:
                i = part.find('\n')
                if i != -1 and part[:i].isspace():
                    part = part[i+1:] 
                part = part.rstrip()
                lines.extend(deindent(part)) 

    def putaround(self, before='', after=''):
        """ return a new source object embedded/indented between before and after. """
        before = Source(before) 
        after = Source(after) 
        lines = ['    ' + line for line in self.lines]
        self.lines = before.lines + lines +  after.lines 

    def __str__(self):
        return "\n".join(self.lines) 

def deindent(pysource):
    """ return a list of deindented lines from the given python
        source code.  The first indentation offset of a non-blank
        line determines the deindentation-offset for all the lines. 
        Subsequent lines which have a lower indentation size will
        be copied verbatim as they are assumed to be part of
        multilines. 
    """
    lines = []
    indentsize = 0
    for line in pysource.split('\n'):
        if not lines:
            if not line.strip():
                continue # skip first empty lines 
            indentsize = len(line) - len(line.lstrip())
        line = line.expandtabs()
        if line.strip():
            if len(line) - len(line.lstrip()) >= indentsize:
                line = line[indentsize:]
        lines.append(line) 

    # treat trailing whitespace-containing lines correctly 
    # (the python parser at least in python 2.2. is picky about it)
    #while lines:
    #    line = lines.pop()
    #    if not line.strip():
    #        continue
    #    lines.append(line)
    #    break
    return lines
