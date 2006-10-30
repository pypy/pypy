
""" Using narcisus to generate code
"""

# 1st attempt - exec the code

import py
import re
from subprocess import Popen, PIPE, STDOUT

class JsSyntaxError(Exception):
    pass

def read_js_output(code_string):
    stripped_code = code_string.replace("\n", "")
    jsdir = py.path.local(__file__).dirpath().join("js")
    jsdefs = jsdir.join("jsdefs.js").read()
    jsparse = jsdir.join("jsparse.js").read()
    pipe = Popen("js", stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    pipe.stdin.write(jsdefs + jsparse + "\n")
    pipe.stdin.write("print(parse('%s'));\n" % stripped_code)
    pipe.stdin.close()
    retval = pipe.stdout.read()
    if retval.startswith(":"):
        raise JsSyntaxError(retval)
    return retval

def parse(code_string):
    read_code = read_js_output(code_string)
    #print read_code
    output = []
    for line in read_code.split("\n"):
        m = re.search('^(\s*)(\w+): (.*?)(,)?$', line)
        if m and (m.group(3) != '{' or m.group(4)):
            output.append("%s'%s': '%s'," % (m.group(1), m.group(2), m.group(3)))
        else:
            m = re.search('^(\s*)(\w+):(.*)$', line)
            if m:
                output.append("%s'%s': %s" % (m.group(1), m.group(2), m.group(3)))
            else:
                output.append(line)

    #print "\n".join(output)
    d = {}
    exec "code =" + "\n".join(output) in d
    return d['code']

