# a couple of support functions which
# help with generating Python source.

import sys, os

def render_docstr(func, indent_str='', closing_str=''):
    """ Render a docstring as a string of lines.
        The argument is either a docstring or an object.
        Note that we don't use a sequence, since we want
        the docstring to line up left, regardless of
        indentation. The shorter triple quotes are
        choosen automatically."""
    if type(func) is not str:
        doc = func.__doc__
    else:
        doc = func
    if doc is None:
        return None
    doc = doc.replace('\\', r'\\')
    compare = []
    for q in '"""', "'''":
        txt = indent_str + q + doc.replace(q[0], "\\"+q[0]) + q + closing_str
        compare.append(txt)
    doc, doc2 = compare
    doc = (doc, doc2)[len(doc2) < len(doc)]
    return doc


class NiceCompile(object):
    """ Compiling parameterized strings in a way that debuggers
        are happy. We provide correct line numbers and a real
        __file__ attribute.
    """
    def __init__(self, namespace):
        srcname = namespace.get('__file__')
        if not srcname:
            # assume the module was executed from the
            # command line.
            srcname = os.path.abspath(sys.argv[-1])
        self.srcname = srcname
        if srcname.endswith('.pyc') or srcname.endswith('.pyo'):
            srcname = srcname[:-1]
        if os.path.exists(srcname):
            self.srcname = srcname
            self.srctext = file(srcname).read()
        else:
            # missing source, what to do?
            self.srctext = None

    def __call__(self, src, args):
        """ instance NiceCompile (src, args) -- formats src with args
            and returns a code object ready for exec. Instead of <string>,
            the code object has correct co_filename and line numbers.
            Indentation is automatically corrected.
        """
        if self.srctext:
            p = self.srctext.index(src)
            prelines = self.srctext[:p].count("\n") + 1
        else:
            prelines = 0
        # adjust indented def
        for line in src.split('\n'):
            content = line.strip()
            if content and not content.startswith('#'):
                break
        # see if first line is indented
        if line and line[0].isspace():
            # fake a block
            prelines -= 1
            src = 'if 1:\n' + src
        src = '\n' * prelines + src % args
        c = compile(src, self.srcname, "exec")
        return c
