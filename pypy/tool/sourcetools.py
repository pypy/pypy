# a couple of support functions which
# help with generating Python source.

def render_docstr(func, indent_str='', closing_str=''):
    """ Render a docstring as a string of lines.
        The argument is either a docstring or an object.
        Note that we don't use a sequence, since we want
        the docstring to line up left, reagrdless of
        indentation."""
    if type(func) is not str:
        doc = func.__doc__
    else:
        doc = func
    if doc is None:
        return None
    compare = []
    for q in '"""', "'''":
        txt = indent_str + q + doc.replace(q[0], "\\"+q[0]) + q + closing_str
        compare.append(txt)
    doc, doc2 = compare
    doc = (doc, doc2)[len(doc2) < len(doc)]
    return doc


