# compare.py <results-file> <reference-results-file>

import sys

def main(cur, ref):
    cur = open(cur, 'rU')
    ref = open(ref, 'rU')
    try:
        while True:
            cur_line = cur.next()
            ref_line = ref.next()
            cur_name, cur_t = cur_line.split()
            ref_name, ref_t = ref_line.split()
            assert cur_name == ref_name
            cur_t = float(cur_t)
            ref_t = float(ref_t)            
            print "%-16s %.06g (x%.02f)" % (cur_name, cur_t, cur_t/ref_t)
    except StopIteration:
        pass

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
