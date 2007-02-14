
""" Some support files for mapping urls, mostly bindings
for existing cgi stuff
"""

import cgi
import urllib

class URL(object):
    def __init__(self, path, vars):
        self.path = path
        self.vars = vars

    def __eq__(self, other):
        if isinstance(other, URL):
            return self.path == other.path and self.vars == other.vars
        if isinstance(other, tuple):
            if len(other) != 2:
                return False
            return self.path, self.vars == other
        return False

    def __ne__(self, other):
        return not self == other

    def __iter__(self):
        return iter((self.path, self.vars))

def parse_url(path):
    """ Parse a/b/c?q=a into ('a', 'b', 'c') {'q':'a'}
    """
    if '?' in path:
        path, var_str = path.split("?")
        vars_orig = cgi.parse_qs(var_str)
        # if vars has a list inside...
        vars = {}
        for i, v in vars_orig.items():
            if isinstance(v, list):
                vars[i] = v[0]
            else:
                vars[i] = v
    else:
        vars = {}
    parts = [urllib.unquote(i) for i in path.split("/") if i]
    return URL(parts, vars)
