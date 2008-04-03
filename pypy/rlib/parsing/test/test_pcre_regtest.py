"""This test can read and parse PCRE regression tests to try out
on our regular expression library.

We currently only test against testoutput7 (DFA tests). We were doing
testoutput1, but that was PCRE matching, which was inconsistent with
our matching on strings like "[ab]{1,3}(ab*|b)" against 'aabbbb'.
"""

# The PCRE library is distributed under the BSD license. We have borrowed some
# of the regression tests (the ones that fit under the DFA scope) in order to
# exercise our regex implementation. Those tests are distributed under PCRE's
# BSD license. Here is the text:

#        PCRE LICENCE
#        ------------
#        
#        PCRE is a library of functions to support regular expressions whose syntax
#        and semantics are as close as possible to those of the Perl 5 language.
#
#        Release 7 of PCRE is distributed under the terms of the "BSD" licence, as
#        specified below. The documentation for PCRE, supplied in the "doc"
#        directory, is distributed under the same terms as the software itself.
#        
#        The basic library functions are written in C and are freestanding. Also
#        included in the distribution is a set of C++ wrapper functions.
#        
#        THE BASIC LIBRARY FUNCTIONS
#        ---------------------------
#        
#        Written by:       Philip Hazel
#        Email local part: ph10
#        Email domain:     cam.ac.uk
#        
#        University of Cambridge Computing Service,
#        Cambridge, England.
#        
#        Copyright (c) 1997-2008 University of Cambridge
#        All rights reserved.
#        
#        THE C++ WRAPPER FUNCTIONS
#        -------------------------
#        
#        Contributed by:   Google Inc.
#        
#        Copyright (c) 2007-2008, Google Inc.
#        All rights reserved.
#        
#        THE "BSD" LICENCE
#        -----------------
#        
#        Redistribution and use in source and binary forms, with or without
#        modification, are permitted provided that the following conditions are met:
#        
#            * Redistributions of source code must retain the above copyright notice,
#              this list of conditions and the following disclaimer.
#        
#            * Redistributions in binary form must reproduce the above copyright
#              notice, this list of conditions and the following disclaimer in the
#              documentation and/or other materials provided with the distribution.
#        
#            * Neither the name of the University of Cambridge nor the name of Google
#              Inc. nor the names of their contributors may be used to endorse or
#              promote products derived from this software without specific prior
#              written permission.
#        
#        THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#        AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#        IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#        ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
#        LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#        CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#        SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#        INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#        CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#        ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#        POSSIBILITY OF SUCH DAMAGE.
#        
#        End

import py
from pypy.rlib.parsing.regexparse import make_runner, unescape
import string
import re

py.test.skip("Still in progress")

def create_pcre_pickle(file, picklefile):
    """Create a filtered PCRE test file for the test. 
    
    The pickle file was created by:
       create_pcre_pickle(open('testoutput1','r'), open('testoutput1.pickle','w')) 
    """
    import pickle

    lines = [line for line in file.readlines()]
    
    # Look for things to skip...
    no_escape = r'(^|[^\\])(\\\\)*'                   # Make sure there's no escaping \
    greedy_ops = re.compile(no_escape + r'[*?+}\(]\?')  # Look for *? +? }? (?
    back_refs  = re.compile(no_escape + r'\(.*' + no_escape + r'\\1') # find a \1
    caret_in_middle = re.compile(no_escape + r'[^\[\\]\^')
    substr_quotes = re.compile(no_escape + r'(\\Q|\\E)')   # PCRE allows \Q.....\E to quote substrings, we dont.
    
    # Perl allows single-digit hex escapes. Change \x0 -> \x00, for example
    expand_perl_hex = re.compile(r'\\x([0-9a-fA-F]{1})(?=[^0-9a-fA-F]|$)')
    
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

        regex = expand_perl_hex.sub(lambda m: r'\x0'+m.group(1), regex)

        tests = []
        if greedy_ops.search(regex) or back_refs.search(regex):
            # Suppress complex features we can't do
            pass
        elif flags:
            # Suppress any test that requires PCRE flags
            pass
        elif caret_in_middle.search(regex):
            pass
        elif substr_quotes.search(regex):
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
            test = expand_perl_hex.sub(lambda m: r'\x0'+m.group(1), test)
            try:
                test = unescape(test)
            except Exception:
                print "Warning: could not unescape %r" % test

            # Third line in the OUTPUT is the result, either:
            # ' 0: ...' for a match (but this is ONLY escaped by \x__ types)
            # 'No match' for no match
            # (other kinds exist, but we ignore them)
            while lines:
                match = lines.pop(0).rstrip('\r\n')
                match = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1),16)), match)
                if match.startswith('No match') or match.startswith('Error'):
                    break
                elif match.startswith(' 0:'):
                    # Now we need to eat any further lines like:
                    # ' 1: ....' a subgroup match
                    while lines[0].strip():
                        # ' 0+ ...' is also possible here
                        if lines[0][2] in [':','+']:
                            lines.pop(0)
                        else:
                            break
                    break
                elif not match:
                    print " *** %r ***" % match
                    raise Exception("Lost sync in output.")
            tests.append((test,match))
    pickle.dump(suite, picklefile)

def get_pcre_pickle(file):
    import pickle
    suite = pickle.load(file)
    return suite

def run_individual_test(regex, tests):
    regex_to_use = regex

    anchor_left = regex_to_use.startswith('^')
    anchor_right = regex_to_use.endswith('$') and not regex_to_use.endswith('\\$')
    if anchor_left:
        regex_to_use = regex_to_use[1:]   # chop the ^ if it's there
    if anchor_right:
        regex_to_use = regex_to_use[:-1]  # chop the $ if it's there

    if not regex_to_use:
        #print "  SKIPPED (Cant do blank regex)"
        return
    
    print "%s:" % regex_to_use
    
    runner = make_runner(regex_to_use)
    # Now run the test expressions against the Regex
    for test, match in tests:
        expect_match = (match != 'No match')
        
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
            if runner.recognize(attempt):
                assert expect_match and attempt==match[4:]
                break
        else:
            assert not expect_match

def run_pcre_tests(suite):
    """Run PCRE tests as given in suite."""
    while suite:
        regex, flags, tests = suite.pop(0)
        yield run_individual_test, regex, tests

def test_output7():
    suite = get_pcre_pickle(open('testoutput7.pickle','r'))
    for test in run_pcre_tests(suite):
        yield test

def generate_output7():
    """Create the testoutput1.pickle file from the PCRE file testoutput1"""
    create_pcre_pickle(open('testoutput7','r'), open('testoutput7.pickle','w'))
        
if __name__=="__main__":
    for fcn, regex, tests in test_output7():
        fcn(regex,tests)