
""" Using narcisus to generate code
"""

# TODO Should be replaced by a real parser

import os
import py
import re
from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.rlib.parsing.ebnfparse import Symbol

DEBUG = False

class JsSyntaxError(Exception):
    pass

singlequote = re.compile(r"(?<!\\)'")
def read_js_output(code_string):
    stripped_code = re.sub(r"\\(?!')",r"\\\\", code_string)
    stripped_code = stripped_code.replace("\n", "\\n")
    stripped_code = singlequote.sub(r"\'", stripped_code)
    if DEBUG:
        print "------ got:"
        print code_string
        print "------ put:"
        print stripped_code
    jsdir = py.path.local(__file__).dirpath().join("js")
    jsdefs = jsdir.join("jsdefs.js").read()
    jsparse = jsdir.join("jsparse.js").read()
    f = py.test.ensuretemp("jsinterp").join("tobeparsed.js")
    f.write(jsdefs+jsparse+"print(parse('%s'));\n" % stripped_code)
    pipe = os.popen("js -f "+str(f), 'r')
    retval = pipe.read()
    if not retval.startswith("{"):
        raise JsSyntaxError(retval)
    return retval

def unquote(t):
    if isinstance(t, Symbol):
        if t.symbol == "QUOTED_STRING":
            t.additional_info = t.additional_info.strip("'")
            t.additional_info = re.sub(r"\\'", r"'", t.additional_info)
    else:
        for i in t.children:
            unquote(i)

def parse(code_string):
    read_code = read_js_output(code_string)
    output = read_code.split(os.linesep)
    t = parse_bytecode("\n".join(output))
    return t

def parse_bytecode(bytecode):
    # print bytecode
    t = parse_tree(bytecode)
    tree = ToAST().transform(t)
    unquote(tree)
    return tree

regexs, rules, ToAST = parse_ebnf(r"""
    QUOTED_STRING: "'([^\']|\\\')*'";"""+"""
    IGNORE: " |\n";
    data: <dict> | <QUOTED_STRING> | <list>;
    dict: ["{"] (dictentry [","])* dictentry ["}"];
    dictentry: QUOTED_STRING [":"] data;
    list: ["["] (data [","])* data ["]"];
""")
parse_tree = make_parse_function(regexs, rules, eof=True)
