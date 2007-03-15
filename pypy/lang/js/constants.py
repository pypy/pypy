escapes = [
    r'\n',
    r'\r',
    r'\f',
    r'\v',
    r'\ ',
    r'\t',
    r"\'",
    r'\b',
    r'\"',
    r'\\']

codes = [
    '\n',
    '\r',
    '\f',
    '\v',
    '\ ',
    '\t',
    "'",
    "\b",
    '"',
    '\\']

escapedict = dict(zip(codes, escapes))
unescapedict = dict(zip(escapes, codes))

SLASH = "\\"