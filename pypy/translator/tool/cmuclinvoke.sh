#!/bin/sh
# Copy this to your PATH
lisp -batch -eval "(compile-file \"$1\")(quit)" >/dev/null 2>&1
lisp -batch -quiet -eval "(load (compile-file-pathname \"$1\"))(quit)"
