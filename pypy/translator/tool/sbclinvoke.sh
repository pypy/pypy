#!/bin/sh
# Copy this to your PATH
sbcl --noinform --disable-debugger --load $1 --eval '(quit)'
