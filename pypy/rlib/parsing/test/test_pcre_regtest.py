# This file can (in progress) read and parse PCRE regression tests to try out
# on our regular expression library.
# 
# To try this out, 'man pcretest' and then grab testinput1 and testoutput1 from 
# the PCRE source code. (I need to look into whether we could distribute these
# files with pypy?)

import py
from pypy.rlib.parsing.regexparse import make_runner, unescape
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
    
def create_regex_iterator(tests, results):
    """Gets a test definition line, formatted per the PCRE spec. This is a 
    generator that returns each regex test."""
    while tests:
        delim = None
        regex = ''
    
        # A line is marked by a start-delimeter and an end-delimeter.
        # The delimeter is non-alphanumeric
        # If a backslash follows the delimiter, then the backslash should
        #   be appended to the end. (Otherwise, \ + delim would not be a
        #   delim anymore!)
        while 1:
            regex += get_simult_lines(tests, results)
    
            if delim is None:
                delim = regex[0]
                assert delim in (set(string.printable) - set(string.letters) - set(string.digits))
                test_re = re.compile(r'%(delim)s(([^%(delim)s]|\\%(delim)s)*([^\\]))%(delim)s(\\?)(.*)' % {'delim': delim})
                # last two groups are an optional backslash and optional flags
            
            matches = test_re.findall(regex)
            if matches:
                break

        assert len(matches)==1
    
        regex = matches[0][0]
        regex += matches[0][-2] # Add the backslash, if we gotta
        flags = matches[0][-1] # Get the flags for the regex

        yield regex, flags

def create_result_iterator(tests, results):
    """Gets the expected return sets for each regular expression."""
    # Second line is the test to run against the regex
    # '    TEXT'
    while 1:
        test = get_simult_lines(tests, results)
        if not test:
            raise StopIteration
        if not test.startswith('    '):
            raise Exception("Input & output match, but I don't understand. (Got %r)" % test)
        if test.endswith('\\'): # Tests that end in \ expect the \ to be chopped off
            assert not test.endswith('\\\\')    # make sure there are no \\ at end
            test = test[:-1]
        test = unescape(test[4:])
    
        # Third line in the OUTPUT is the result, either:
        # ' 0: ...' for a match (but this is ONLY escaped by \x__ types)
        # 'No match' for no match
        result = results.pop(0)
        result = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1),16)), result)
        if result == 'No match':
            pass
        elif result.startswith(' 0:'):
            # Now we need to eat any further lines like:
            # ' 1: ....' a subgroup match
            while results[0]:
                if results[0][2] == ':':
                    results.pop(0)
                else:
                    break
        else:
            raise Exception("Lost sync in output.")
        yield test, result
    
class SkipException(Exception):
    pass
    
def test_file():
    """Open the PCRE tests and run them."""
    tests = [line.rstrip() for line in open('testinput1','r').readlines()]
    results = [line.rstrip() for line in open('testoutput1','r').readlines()]
    
    regex_flag_mapping = { '': lambda s: s, 
                           'i': lambda s: s.upper()
                         }
    
    regex_set = create_regex_iterator(tests, results)    
    import pdb
    for regex, regex_flags in regex_set:
        try:
            print '%r' % regex

            # Create an iterator to grab the test/results for this regex
            result_set = create_result_iterator(tests, results)

            # Handle the flags:
            if regex_flags in regex_flag_mapping:
                text_prepare = regex_flag_mapping[regex_flags]
            elif 'x' in regex_flags:
                raise SkipException("Cant do extended PRCE expressions")            
            else:
                print "UNKNOWN FLAGS: %s" % regex_flags
                continue
        
            skipped = any([op in regex for op in ['*?', '??', '+?', '}?', '(?']])        
            if skipped:
                raise SkipException("Cant do non-greedy operators or '(?' constructions)")
                
            regex_to_use = text_prepare(regex)
        
            anchor_left = regex_to_use.startswith('^')
            anchor_right = regex_to_use.endswith('$') and not regex_to_use.endswith('\\$')
            if anchor_left:
                regex_to_use = regex_to_use[1:]   # chop the ^ if it's there
            if anchor_right:
                regex_to_use = regex_to_use[:-1]  # chop the $ if it's there
        
            if not regex_to_use:
                raise SkipException("Cant do blank regex")
        except SkipException, e:
            print "  SKIPPED (%s)" % e.message
            # now burn all the tests for this regex
            for _ in result_set:
                pass
            continue
            
        # Finally, we make the pypy regex runner
        runner = make_runner(regex_to_use)
        
        # Now run the test expressions against the Regex
        for test, result in result_set:
            # Create possible subsequences that we should test
            if anchor_left:
                start_range = [0]
            else:
                start_range = range(0, len(test))
            
            if anchor_right:
                subseq_gen = ( (start, len(test)) for start in start_range )
            else:
                # Go backwards to simulate greediness
                subseq_gen = ( (start, end) for start in start_range for end in range(len(test)+1, start, -1) )

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
                    print "  pass:        regex==%r test==%r" % (regex, test)
            elif result.startswith(' 0: '):
                if not matched:
                    print "  MISSED:      regex==%r test==%r" % (regex, test)
                elif not attempt==text_prepare(result[4:]):
                    print "  BAD MATCH:   regex==%r test==%r found==%r expect==%r" % (regex, test, attempt, result[4:])
                else:
                    print "  pass:        regex==%r test==%r" % (regex, test)
