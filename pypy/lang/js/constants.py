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
    r'\\',
    r'\u'] #don't know what to do with these

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
    '\\',
    'u']

escapedict = dict(zip(codes, escapes))
unescapedict = dict(zip(escapes, codes))

SLASH = "\\"