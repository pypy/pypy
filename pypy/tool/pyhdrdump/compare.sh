#!/bin/sh
# Compare two pyhdrdump outputs and categorise the differences.
#
# Usage: ./compare.sh CPYTHON.dump PYPY.dump
#
# PyPy implements almost every public function as a macro that forwards to a
# `PyPy`-prefixed symbol, so a raw diff is all noise.  This strips the
# "/* macro, real name ... */" annotation from both sides before comparing, so
# only meaningful divergences remain, split into three buckets:
#   A) name is a #define in one header but a real function in the other
#   B) name is a function in both, but the normalized signature differs
#   C) name present in one header only
set -e

CPY="$1"
PYPY="$2"
[ -n "$CPY" ] && [ -n "$PYPY" ] || { echo "usage: $0 CPYTHON.dump PYPY.dump" >&2; exit 2; }

TAB=$(printf '\t')

# name<TAB>signature, alias comment stripped, sorted by name.
keyed() {
    sed -E 's@ /\* macro, real name [A-Za-z0-9_]+ \*/@@' "$1" | awk -v OFS="$TAB" '
    {
        if (substr($0,1,7)=="#define") { n=$2; sub(/\(.*/,"",n) }
        else { p=index($0,"("); pre=substr($0,1,p-1); m=split(pre,a," "); n=a[m] }
        print n, $0
    }' | sort -t"$TAB" -k1,1
}

C=$(mktemp); P=$(mktemp); CN=$(mktemp); PN=$(mktemp)
trap 'rm -f "$C" "$P" "$CN" "$PN"' EXIT
keyed "$CPY"  > "$C"
keyed "$PYPY" > "$P"
cut -f1 "$C" > "$CN"
cut -f1 "$P" > "$PN"

both=$(join -t"$TAB" -j1 -o 1.2,2.2 "$C" "$P")

echo "=== A) CPython #define  vs  PyPy function ==="
printf '%s\n' "$both" | awk -F"$TAB" '$1!=$2 && $1 ~ /^#define/ && $2 !~ /^#define/{print "  CPY  "$1"\n  PYPY "$2"\n"}'

echo "=== B) function in both, signature differs ==="
printf '%s\n' "$both" | awk -F"$TAB" '$1!=$2 && $1 !~ /^#define/ && $2 !~ /^#define/{print "  CPY  "$1"\n  PYPY "$2"\n"}'

echo "=== C) present in CPython only ==="
comm -23 "$CN" "$PN" | sed 's/^/  /'
echo "=== C) present in PyPy only ==="
comm -13 "$CN" "$PN" | sed 's/^/  /'
