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

def read_file(file):
    lines = [line for line in file.readlines()]
    
    # Look for things to skip...
    no_escape = r'(^|[^\\])(\\\\)*'                   # Make sure there's no escaping \
    greedy_ops = re.compile(no_escape + r'[*?+}\(]\?')  # Look for *? +? }? (?
    back_refs  = re.compile(no_escape + r'\(.*' + no_escape + r'\\1') # find a \1
    
    # suite = [ 
    #            [regex, flags, [(test,result),(test,result),...]]
    #            [regex, flags, [(test,result),(test,result),...]]
    #         ]
    suite = []
    while lines:
        delim = None
        regex = ''
        # A line is marked by a start-delimeter and an end-delimeter.
        # The delimeter is non-alphanumeric
        # If a backslash follows the delimiter, then the backslash should
        #   be appended to the end. (Otherwise, \ + delim would not be a
        #   delim anymore!)
        while 1:
            regex += lines.pop(0)
            if not delim:
                if not regex.strip():   # Suppress blank lanes before delim
                    regex = ''
                    continue
                delim = regex.strip()[0]
                assert delim in (set(string.printable) - set(string.letters) - set(string.digits))
                test_re = re.compile(r'%(delim)s(([^%(delim)s]|\\%(delim)s)*([^\\]))%(delim)s(\\?)([^\n\r]*)' % {'delim': delim})
                # last two groups are an optional backslash and optional flags
            
            matches = test_re.findall(regex)
            if matches:
                break

        assert len(matches)==1  # check to make sure we matched right
    
        regex = matches[0][0]
        regex += matches[0][-2] # Add the backslash, if we gotta
        flags = matches[0][-1] # Get the flags for the regex

        tests = []

        if greedy_ops.search(regex) or back_refs.search(regex):
            # Suppress complex features we can't do
            pass
        elif flags:
            # Suppress any test that requires PCRE flags
            pass
        else:
            # In any other case, we're going to add the test
            # All the above test fall through and DONT get appended
            suite.append([regex, flags, tests]) 
            
        # Now find the test and expected result
        while lines:
            test = lines.pop(0).strip()
            if not test:
                break   # blank line ends the set
            if test.endswith('\\'): # Tests that end in \ expect the \ to be chopped off
                assert not test.endswith('\\\\\\') # Make sure not three \'s. otherwise this check will get ridiculous
                if not test.endswith('\\\\'): # Two \'s means a real \
                    test = test[:-1]
            test = unescape(test)

            # Third line in the OUTPUT is the result, either:
            # ' 0: ...' for a match (but this is ONLY escaped by \x__ types)
            # 'No match' for no match
            match = lines.pop(0).rstrip('\r\n')
            match = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1),16)), match)
            if match.startswith('No match'):
                pass
            elif match.startswith(' 0:'):
                # Now we need to eat any further lines like:
                # ' 1: ....' a subgroup match
                while lines[0].strip():
                    # ' 0+ ...' is also possible here
                    if lines[0][2] in [':','+']:
                        lines.pop(0)
                    else:
                        break
            else:
                print " *** %r ***" % match
                raise Exception("Lost sync in output.")
            tests.append((test,match))
    return suite

def test_file():
    """Open the PCRE tests and run them."""
    suite = read_file(open('testoutput1','r'))
        
    import pdb
    while suite:
        regex, flags, tests = suite.pop(0)
        print '/%r/%s' % (regex, flags)
    
        regex_to_use = regex
    
        anchor_left = regex_to_use.startswith('^')
        anchor_right = regex_to_use.endswith('$') and not regex_to_use.endswith('\\$')
        if anchor_left:
            regex_to_use = regex_to_use[1:]   # chop the ^ if it's there
        if anchor_right:
            regex_to_use = regex_to_use[:-1]  # chop the $ if it's there
    
        if not regex_to_use:
            print "  SKIPPED (Cant do blank regex)"
            continue
            
        # Finally, we make the pypy regex runner
        runner = make_runner(regex_to_use)
        
        # Now run the test expressions against the Regex
        for test, match in tests:
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
                attempt = test[start:end]
                matched = runner.recognize(attempt)
                if matched: 
                    break
            
            # Did we get what we expected?
            if match == 'No match':
                if matched:
                    print "  FALSE MATCH: regex==%r test==%r" % (regex, test)
                else:
                    pass
                    #print "  pass:        regex==%r test==%r" % (regex, test)
            elif match.startswith(' 0: '):
                if not matched:
                    print "  MISSED:      regex==%r test==%r" % (regex, test)
                elif not attempt==match[4:]:
                    print "  BAD MATCH:   regex==%r test==%r found==%r expect==%r" % (regex, test, attempt, match[4:])
                else:
                    pass
                    #print "  pass:        regex==%r test==%r" % (regex, test)
