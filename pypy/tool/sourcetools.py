# a couple of support functions which
# help with generating Python source.

def render_docstr(func, indent_str='', closing_str='', q='"""', redo=True):
    """ Render a docstring as a sequence of lines.
        The argument is either a docstring or an object"""
    if type(func) is not str:
        doc = func.__doc__
    else:
        doc = func
    if doc is None:
        return []
    doc = indent_str + q + doc.replace(q, "\\"+q) + q + closing_str
    doc2 = doc
    if q in doc and redo:
        doc2 = render_docstr(func, indent_str, closing_str, "'''", False)
    if not redo:
        return doc # recursion case
    doc = (doc, doc2)[len(doc2) < len(doc)]
    return [line for line in doc.split('\n')]

