import sys
import re
import parser

blank_re=re.compile(r"\s*(#.*)?")

def get_indent(line):
    indent = re.match(blank_re,line).group()
    return indent, indent==line

def read_whole_suite(intro_line):
    base_indent, dummy = get_indent(intro_line)
    lines = []
    cont = []
    parsing_prefix = ""
    if len(base_indent) > 0:
	parsing_prefix = "if 0:\n"
    while True:
	line = f.readline()
	if not line:
	    break
   	indent, isblank = get_indent(line)
        if isblank:
	    pass
        elif cont:
	    cont.append(line)
	    try:
		parser.suite(parsing_prefix+''.join(cont))
	    except SyntaxError:
		pass 
	    else:
		cont = []
        else:
	    if len(indent) <= len(base_indent):
		pushback.append(line)
		break
	    try:
		parser.suite(parsing_prefix+line)
	    except SyntaxError:
		cont = [line]
	lines.append(line)

    return base_indent,lines

pass_re = re.compile(r"^\s*pass\s*$")
getobjspace_re = r"testit\.objspace\((.*)\)"
setspace_re = r"self\.space\s*=\s*"

def up_down_port(lines):
    npass = 0
    nblank = 0
    objspace = None
    n = -1
    for line in lines:
        n += 1
	dummy, isblank = get_indent(line)
	if isblank:
	    nblank += 1
	    continue
	if re.match(pass_re, line):
	    npass += 1
	    continue
	m = re.search(getobjspace_re, line)
	if m:
	    objspace = m.group(1)
	    line = line[:m.start()]+"self.space"+line[m.end():]
	    line = re.sub(setspace_re,"",line)
	    if line.strip() == "self.space":
		line = ""
		nblank += 1
	    lines[n] = line

    skip = npass+nblank == len(lines)

    return objspace,skip
	    
for fn in sys.argv[1:]:
    print fn
    lines = []
    pushback = []
    kind = None
    f = file(fn, 'r')

    confused = False
    while True:
        if pushback:
	    line = pushback.pop()
	else:
	    line = f.readline()
        if not line:
            break
        rline = line.rstrip()
        if rline == 'from pypy.tool import testit':
            continue
        if (rline == "if __name__ == '__main__':" or
            rline == 'if __name__ == "__main__":'):
            tail = f.read()
            if tail.strip() != 'testit.main()':
                print ' * uncommon __main__ lines at the end'
		confused = True
            break
        if line.strip() == 'def setUp(self):':
            base_indent,suite = read_whole_suite(line)
	    objspace,skip = up_down_port(suite)
	    #print suite
	    if objspace:
		lines.append(base_indent+"objspacename = %s\n" % objspace)
		lines.append("\n")
	    if not skip:
		lines.append(base_indent+"def setup_method(self,method):\n")
		lines.extend(suite)
	    continue
        if line.strip() == 'def tearDown(self):':
            base_indent, suite = read_whole_suite(line)
            unexpected,skip = up_down_port(suite)
	    if unexpected is not None:
		print "* testit.objspace(<name>) in tearDown"
		confused = True
	    #print suite
	    if not skip:
		lines.append(base_indent+"def teardown_method(self,method):\n")
		lines.extend(suite)
	    continue
        if line.startswith('class '):
            rest = line[6:].strip()
            if rest.endswith('(testit.AppTestCase):'):
                rest = rest[:-21].strip() + ':'
                if not rest.startswith('AppTest'):
                    if not rest.startswith('Test'):
                        rest = 'Test'+rest
                    rest = 'App'+rest
		kind = 'app-test'
            elif rest.endswith('(testit.IntTestCase):'):
                rest = rest[:-21].strip() + ':'
                if not rest.startswith('Test'):
                    rest = 'Test'+rest
                kind = 'test'
            elif rest.endswith('(testit.TestCase):'):
                rest = rest[:-18].strip() + ':'
                if not rest.startswith('Test'):
                    rest = 'Test'+rest
                kind = 'test'
            else:
                print ' * ignored class', rest
            line = 'class ' + rest + '\n'
        lines.append(line)
    f.close()

    while lines and not lines[-1].strip():
        del lines[-1]
    
    if confused: 
	print "** confused: file not changed"
    else:
	#sys.stdout.writelines(lines)
	f = file(fn, 'w')
	f.writelines(lines)
	f.close()
