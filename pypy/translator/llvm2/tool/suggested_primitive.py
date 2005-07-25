#!/usr/bin/python

import os

def main():

    ll_modules_path = '../../../rpython/module'
    ll_files = [ll_modules_path + '/' + f for f in os.listdir(ll_modules_path) if f[:3] == 'll_' and f[-3:] == '.py']
    ll_function = {}    #XXX better use sets
    for ll_file in ll_files:
        for s in file(ll_file):
            s = s.strip()
            if not s.startswith('ll_') or s.find('suggested_primitive') == -1 or s.find('True') == -1:
                continue
            ll_function[s.split('.')[0]] = True

    llvm_modules_path = '..'
    llvm_files = [llvm_modules_path + '/' + 'extfunction.py']
    llvm_function = {}
    for llvm_file in llvm_files:
        t = 'extfunctions["%'
        for s in file(llvm_file):
            s = s.strip()
            if not s.startswith(t):
                continue
            llvm_function[s.split('"')[1][1:]] = True

    print 'rpython suggested primitives:'
    print ll_function.keys()
    print

    print 'llvm implemented functions:'
    print llvm_function.keys()
    print

    print 'llvm missing primitives:'
    missing_functions = [func for func in ll_function.keys() if func not in llvm_function]
    print missing_functions
    print

if __name__ == '__main__':
    main()
