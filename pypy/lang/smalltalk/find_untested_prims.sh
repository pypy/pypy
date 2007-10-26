#!/bin/sh
grep '^[A-Z][A-Z_]' primitives.py | awk '{print $1;}' | sort | uniq > pcodes.1
grep 'primitives.[A-Z][A-Z_]' test/test_primitives.py | sed 's/.*primitives.\([A-Z_]*\).*/\1/g' | sort | uniq > pcodes.2
echo Untested primitive codes:
diff pcodes.1 pcodes.2 | grep "<"
