#!/bin/sh
# Build pyhdrdump against libclang.  Needs libclang + its dev headers
# (Debian/Ubuntu: `apt install libclang-18-dev`).
#
# Works from any directory: source and binary are resolved relative to this
# script, not the current working directory.
set -e

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

LLVM_CONFIG="${LLVM_CONFIG:-llvm-config-18}"
INCDIR="$($LLVM_CONFIG --includedir)"
LIBDIR="$($LLVM_CONFIG --libdir)"

# libclang ships only a versioned .so on some distros, so link it by full path
# rather than relying on -lclang finding an unversioned symlink.
LIBCLANG="$LIBDIR/libclang.so"
[ -f "$LIBCLANG" ] || LIBCLANG="$LIBDIR/libclang.so.1"

CXX="${CXX:-clang++-18}"
"$CXX" -std=c++17 -O2 -Wall -I"$INCDIR" \
    "$HERE/pyhdrdump.cpp" "$LIBCLANG" \
    -Wl,-rpath,"$LIBDIR" -o "$HERE/pyhdrdump"

echo "built $HERE/pyhdrdump"
