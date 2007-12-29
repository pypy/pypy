"""
Run this script to regenerate all the output/snippet_*.txt.
Then use 'svn diff' to review all the changes!
"""

from pypy.interpreter.pyparser.test import test_snippet_out

def test_main():
    import pypy.conftest
    space = pypy.conftest.gettestobjspace('std')
    for snippet_name in test_snippet_out.SNIPPETS:
        print snippet_name
        output = test_snippet_out.generate_output(snippet_name, space)
        path = test_snippet_out.get_output_path(snippet_name)
        f = open(path, 'w')
        f.write(output)
        f.close()

if __name__ == '__main__':
    test_main()
