import sys


for fn in sys.argv[1:]:
    print fn
    lines = []
    f = file(fn, 'r')
    while True:
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
            break
        if line.strip() == 'def setUp(self):':
            print ' * setUp() ignored'
        if line.strip() == 'def tearDown(self):':
            print ' * tearDown() ignored'
        if line.startswith('class '):
            rest = line[6:].strip()
            if rest.endswith('(testit.AppTestCase):'):
                rest = rest[:-21].strip() + ':'
                if not rest.startswith('AppTest'):
                    if not rest.startswith('Test'):
                        rest = 'Test'+rest
                    rest = 'App'+rest
            elif rest.endswith('(testit.IntTestCase):'):
                rest = rest[:-21].strip() + ':'
                if not rest.startswith('Test'):
                    rest = 'Test'+rest
            elif rest.endswith('(testit.TestCase):'):
                rest = rest[:-18].strip() + ':'
                if not rest.startswith('Test'):
                    rest = 'Test'+rest
            else:
                print ' * ignored class', rest
            line = 'class ' + rest + '\n'
        lines.append(line)
    f.close()

    while lines and not lines[-1].strip():
        del lines[-1]

    f = file(fn, 'w')
    f.writelines(lines)
    f.close()
