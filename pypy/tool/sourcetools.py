# a couple of support functions which
# help with generating Python source.

# this script is used for extracting
# the information available for exceptions
# via introspection.
# The idea is to use it once to create
# a template for a re-birth of exceptions.py

def render_docstr(func, indent_str, q='"""', redo=True):
    """render a docstring as a sequenceof lines """
    doc = func.__doc__
    if doc is None:
        return []
    doc = indent_str + q + doc.replace(q, "\\"+q) + q
    doc2 = doc
    if q in doc and redo:
        doc2 = render_docstr(func, indent_str, "'''", False)
    if not redo:
        return doc # recursion case
    doc = (doc, doc2)[len(doc2) < len(doc)]
    return [line for line in doc.split('\n')]

