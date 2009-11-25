#!/bin/sh

awk '/W_ContextPart\./ {print $0;}' interpreter.py \
    | sed -e 's/.*W_ContextPart\.\(.*\)),/\1/' \
    | sort -u \
        > bcodes.1
cat test/test_interpreter.py \
    | sed 's/[^A-Za-z]/ /g' \
    | tr ' ' '\n' \
    | grep '[a-z]' \
    | sort -u \
        > bcodes.2

echo Untested byte-codes:
diff bcodes.1 bcodes.2 \
    | grep "<"
rm bcodes.1 bcodes.2