# This file can (in progress) read and parse PCRE regression tests to try out
# on our regular expression library.
# 
# To try this out, 'man pcretest' and then grab testinput1 and testoutput1 from 
# the PCRE source code. (I need to look into whether we could distribute these
# files with pypy?)

import py
from pypy.rlib.parsing.regexparse import make_runner, unescape, RegexParser
import string
import re

py.test.skip("In Progress...")

def get_simult_lines(tests, results, test_line_num=0):
    """Returns a line from the input/output, ensuring that
    we are sync'd up between the two."""
    test = tests.pop(0)
    result = results.pop(0)
    
    test_line_num += 1
    
    if test != result:
        raise Exception("Lost sync between files at input line %d.\n  INPUT: %s\n  OUTPUT: %s" % (test_line_num, test, result))
        
    return test
    
def get_definition_line(tests, results):
    """Gets a test definition line, formatted per the PCRE spec."""
    delim = None
    test = ''
    result = ''
    
    # A line is marked by a start-delimeter and an end-delimeter.
    # The delimeter is non-alphanumeric
    # If a backslash follows the delimiter, then the backslash should
    #   be appended to the end. (Otherwise, \ + delim would not be a
    #   delim anymore!)
    while 1:
        test += get_simult_lines(tests, results)
    
        if delim is None:
            delim = test[0]
            assert delim in (set(string.printable) - set(string.letters) - set(string.digits))
            test_re = re.compile(r'%(delim)s(([^%(delim)s]|\\%(delim)s)*([^\\]))%(delim)s(\\?)(.*)' % {'delim': delim})
        
        matches = test_re.findall(test)
        if matches:
            break

    assert len(matches)==1
    test = matches[0][0]
    
    # Add the backslash, if we gotta
    test += matches[0][-2]
    flags = matches[0][-1]

    return test, flags
    
def get_test_result(tests, results):
    """Gets the expected return from the regular expression"""
    # Second line is the test to run against the regex
    # '    TEXT'
    test = get_simult_lines(tests, results)
    if not test:
        return None, None
    if not test.startswith('    '):
        raise Exception("Input & output match, but I don't understand. (Got %r)" % test)
    test = unescape(test[4:])
    
    # Third line in the OUTPUT is the result, either:
    # ' 0: ...' for a match
    # 'No match' for no match
    result = unescape(results.pop(0))
    if result == 'No match':
        pass
    elif result.startswith(' 0: '):
        # Now we need to eat any further lines like:
        # ' 1: ....' a subgroup match
        while results[0]:
            if results[0][2] == ':':
                results.pop(0)
            else:
                break
    else:
        raise Exception("Lost sync in output.")
    return test, result
    
def test_file():
    """Open the PCRE tests and run them."""
    tests = [line.rstrip() for line in open('testinput1','r').readlines()]
    results = [line.rstrip() for line in open('testoutput1','r').readlines()]
    
    regex_flag_mapping = { '': lambda s: s, 
                           'i': lambda s: s.upper()
                         }
    
    import pdb
    while tests:
        # First line is a test, in the form:
        # '/regex expression/FLAGS'
        regex, regex_flags = get_definition_line(tests, results)

        # Handle the flags:
        try:
            text_prepare = regex_flag_mapping[regex_flags]
        except KeyError:
            print "UNKNOWN FLAGS: %s" % regex_flags
            continue
        
        print '%r' % regex

        skipped = any([op in regex for op in ['*?', '??', '+?', '}?']])        
        if skipped:
            print "  SKIPPED (cant do non-greedy operators)"
            # now burn all the tests for this regex
            while 1:
                test, result = get_test_result(tests, results)
                if not test:
                    break   # A blank line means we have nothing to do
            continue
                
        regex_to_use = text_prepare(regex)
        
        anchor_left = regex_to_use.startswith('^')
        anchor_right = regex_to_use.endswith('$') and not regex_to_use.endswith('\\$')
        if anchor_left:
            regex_to_use = regex_to_use[1:]   # chop the ^ if it's there
        if anchor_right:
            regex_to_use = regex_to_use[:-1]  # chop the $ if it's there
        
        # Finally, we make the pypy regex runner
        runner = make_runner(regex_to_use)

        # Now run the test expressions against the Regex
        while 1:
            test, result = get_test_result(tests, results)
            if not test:
                break   # A blank line means we have nothing to do
                
            # Create possible subsequences that we should test
            if anchor_left:
                subseq_gen = [0]
            else:
                subseq_gen = (start for start in range(0, len(test)))
            
            if anchor_right:
                subseq_gen = ( (start, len(test)) for start in subseq_gen )
            else:
                # Go backwards to simulate greediness
                subseq_gen = ( (start, end) for start in subseq_gen for end in range(len(test)+1, start+1, -1) )

            # Search the possibilities for a match...
            for start, end in subseq_gen:
                attempt = text_prepare(test[start:end])
                matched = runner.recognize(attempt)
                if matched: 
                    break
            
            # Did we get what we expected?
            if result == 'No match':
                if matched:
                    print "  FALSE MATCH: regex==%r test==%r" % (regex, test)
                else:
                    print "  pass       : regex==%r test==%r" % (regex, test)
            elif result.startswith(' 0: '):
                if not matched:
                    print "  MISSED:      regex==%r test==%r" % (regex, test)
                elif not attempt==text_prepare(result[4:]):
                    print "  BAD MATCH:   regex==%r test==%r found==%r expect==%r" % (regex, test, attempt, result[4:])
                else:
                    print "  pass       : regex==%r test==%r" % (regex, test)
