"""
    creating code objects and keeping track of their source code 
    with artificial unique filenames. Provides and extends some 
    'inspect' functions which usually only work with code coming 
    from static modules. 
"""
from __future__ import generators
import sys
import inspect
import os
import re
from linecache import getline as linecache_getline
from linecache import getlines as linecache_getlines
from inspect import findsource as inspect_findsource
import linecache
import __builtin__
from __builtin__ import compile as oldcompile 
from py import magic

def gettb(tb, n=-1):
    """ return the n'th traceback. """
    return listtb(tb)[n]

def listtb(tb):
    tblist = []
    while tb:
        tblist.append(tb)
        tb = tb.tb_next
    return tblist

def getparseablestartingblock(obj): 
    if hasattr(obj, 'tb_lineno'): 
        lineno = obj.tb_lineno-1
        frame = obj.tb_frame
    elif hasattr(obj, 'f_lineno'):
        lineno = obj.f_lineno-1
        frame = obj
    else:
        raise ValueError, "can only grok frame and traceback objects" 
    #lineno_hint = frame.f_lineno - 1 
    #print "getstartingblock: lineno_hint is %d" % lineno_hint 
    lines = magic.dyncode.getlines(frame.f_code.co_filename) 
    source = getsource_tryparsing(lines, lineno) 
    #print "getstartingblock: returning %r" % source
    return source 

def getsource_tryparsing(lines, lineno_hint):
    # the famous try-parsing technique is back! :-) 
    # first we go forward, afterwards we try parsing backwards, i don't
    # see how we could do better ...  given that a multiline assert
    # statement has its frame.f_lineno set to the first line, while
    # 'A(x,\n  y)' will have its frame.f_lineno set to the second line 
    current = lineno_hint 
    while current < len(lines)+1: 
        source = "".join(lines[lineno_hint:current+1])
        source = source.lstrip()
        if isparseable(source):
            return source 
        current += 1

    current = lineno_hint 
    while current >= 0:
        source = "".join(lines[current:lineno_hint+1]) 
        source = source.lstrip()
        if isparseable(source):
            return source 
        current -= 1

def isparseable(source):
    import parser
    try:
        parser.suite(source)
    except (parser.ParserError, SyntaxError):
        return False
    else:
        return True 

_dynfileregistry = {}

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
        lines.append(line + '\n')

    # treat trailing whitespace-containing lines correctly 
    # (the python parser at least in python 2.2. is picky about it)
    while lines:
        line = lines.pop()
        if not line.strip():
            continue
        if not line.endswith('\n'):
            line = line + '\n'
        lines.append(line)
        break
    return lines

def compile2(source, mode='exec', flag=generators.compiler_flag):
    frame = inspect.currentframe(1) # the caller
    return newcompile(frame, source, mode, flag) 

def newcompile(frame, source, mode='exec', flag=generators.compiler_flag):
    lines = deindent(source)
    source = "".join(lines)
    origin = "%s:%d" % (frame.f_code.co_filename, frame.f_lineno)
    filename = _makedynfilename(origin, lines)
    #print "frames filename", frame.f_code.co_filename
    #print "making dynfilename", filename
    try:
        #print "compiling source:", repr(source)
        co = oldcompile(source+'\n', filename, mode, flag)
    except SyntaxError, ex:
        # re-represent syntax errors from parsing python strings 
        newex = SyntaxError('\n'.join([
            "".join(lines[:ex.lineno]),
            " " * ex.offset + '^', 
            "syntax error probably generated here: %s" % origin]))
        newex.offset = ex.offset
        newex.lineno = ex.lineno
        newex.text = ex.text
        raise newex
    _dynfileregistry[filename] = origin, lines, co 
    return co

def compile(source, filename, mode='exec', flag=generators.compiler_flag):
    frame = inspect.currentframe(1) # the caller
    return newcompile(frame, source, mode, flag) 
    
def invoke():
    # a hack for convenience of displaying tracebacks 
    magic.patch(linecache, 'getline', getline)
    magic.patch(linecache, 'getlines', getlines)
    magic.patch(__builtin__, 'compile', compile)
    magic.patch(inspect, 'findsource', findsource)

def revoke():
    magic.revert(linecache, 'getline') 
    magic.revert(linecache, 'getlines') 
    magic.revert(__builtin__, 'compile') 
    magic.revert(inspect, 'findsource') 

def tbinfo(tb, index = -1):
    """ return an (filename:lineno, linecontent) tuple for the given 
        traceback.  Works also with code generated from compile2(). 
    """
    tb = gettb(tb, index)
    filename = tb.tb_frame.f_code.co_filename
    lineno = tb.tb_lineno 
    return filename, lineno

def getframe(tb, index = -1):
    """ return an (filename:lineno, linecontent) tuple for the given 
        traceback.  Works also with code generated from compile2(). 
    """
    tb = gettb(tb, index)
    return tb.tb_frame

def _makedynfilename(origin, source, originmap={}):
    origin = origin
    entry = originmap.setdefault(origin, [])
    num = len(entry)
    entry.append(num)
    if num > 0:
        return "<%s [%d]>" % (origin, num)
    else:
        return "<%s>" % origin 

def getline(filename, lineno):
    """ return line in filename (possibly dyncode). """
    tup = _dynfileregistry.get(filename, None)
    if tup is not None:
        origin, lines, co = tup
        return lines[lineno-1]
    else:
        return linecache_getline(filename, lineno)

def getlines(filename): 
    """ return line in filename (possibly dyncode). """
    tup = _dynfileregistry.get(filename, None)
    if tup is not None:
        origin, lines, co = tup
        return lines 
    else:
        return linecache_getlines(filename) 


def findsource(obj):
    try:
        return inspect_findsource(obj)
    except (TypeError, IOError):
        code = getcode(obj)
        filename = obj._co_filename
        if not _dynfileregistry.has_key(filename):
            raise
        origin, lines, gencode = _dynfileregistry[filename]
        firstlineno = code.co_firstlineno - 1 
        lines = inspect.getblock(lines[firstlineno:])
        return "".join(lines), firstlineno

def getcode(obj):
    if inspect.iscode(obj):
        return obj
    for name in ('func_code', 'f_code'):
        if hasattr(obj, name):
            return getattr(obj, name)
        
def getsourcelines(object):
    """Return a list of source lines and starting line number for an object.

    The argument may be a module, class, method, function, traceback,
    frame, or (a dynamically created) code object.  The source code is
    returned as a list of the lines corresponding to the object and the
    line number indicates where in the original source file the first
    line of code was found.  An IOError is raised if the source code
    cannot be retrieved.
    """
    lines, lnum = findsource(object)
    if inspect.ismodule(object): 
        return lines, 0
    else: 
        return inspect.getblock(lines[lnum:]), lnum + 1

def getsource(object):
    """Return the text of the source code for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a single string.  An
    IOError is raised if the source code cannot be retrieved."""
    lines, lnum = getsourcelines(object)
    return ''.join(lines)

def findsource(obj):
    try:
        return inspect_findsource(obj)
    except IOError:
        obj = getcode(obj)
        filename = obj.co_filename
        if _dynfileregistry.has_key(filename):
            origin, lines, gencode = _dynfileregistry[filename]
    
            lnum = obj.co_firstlineno - 1
            pat = re.compile(r'^(\s*def\s)|(.*\slambda(:|\s))')
            while lnum > 0:
                if pat.match(lines[lnum]): break
                lnum = lnum - 1
            return lines, lnum
        raise IOError, "could not get source (even after looking in the code registry)"

def getpyfile(obj):
    fn = inspect.getfile(obj)
    if fn.endswith('.pyc'):
        fn = fn[:-1]
    assert fn.endswith('.py')
    return fn
