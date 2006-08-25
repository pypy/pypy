#!/bin/bash

#This should be run from the directory where you checked out pypy-dist

svn up rpython2javascript

rm -f dist/*.egg
python ./rpython2javascript/pypy/translator/js/turbogears/setup.py bdist_egg
scp dist/*.egg ericvrp@codespeak.net:public_html/rpython2javascript

#python ./rpython2javascript/pypy/translator/js/turbogears/setup.py register
