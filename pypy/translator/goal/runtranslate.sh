export RTYPERORDER=order,module-list.pedronis 
# stopping on the first error
#python translate_pypy.py -no-c -no-o -text  -no-snapshot -fork
# running it all 
python translate_pypy.py -no-c -no-o -text -t-insist -no-snapshot -fork
