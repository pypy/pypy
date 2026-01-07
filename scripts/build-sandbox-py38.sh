#!/bin/bash
set -euo pipefail

# Build script for sandboxed PyPy3.8 (macOS)
# Uses pypy/pypy2.7 detection for Homebrew compatibility

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYPY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== PyPy3.8 Sandbox Build Script ==="
echo "PyPy root: ${PYPY_ROOT}"
echo ""

# Detect pypy2.7 (prefer pypy2.7, fallback to pypy for Homebrew)
if command -v pypy2.7 &> /dev/null; then
    PYPY_CMD="pypy2.7"
elif command -v pypy &> /dev/null; then
    PYPY_CMD="pypy"
else
    echo "ERROR: pypy2.7 or pypy not found in PATH"
    echo "Please ensure PyPy 2.7 is installed"
    exit 1
fi

echo "Using PyPy: $(which $PYPY_CMD)"
$PYPY_CMD --version
echo ""

# Verify cffi
if ! $PYPY_CMD -c "import cffi" &> /dev/null; then
    echo "ERROR: cffi module not found for $PYPY_CMD"
    echo "Install it with: $PYPY_CMD -m pip install cffi"
    exit 1
fi
echo "cffi module: OK"
echo ""

cd "${PYPY_ROOT}"

# Navigate to goal directory
cd "${PYPY_ROOT}/pypy/goal"
echo "Working directory: $(pwd)"
echo ""

# Start build
echo "=== Starting RPython Translation ==="
echo "This will take approximately 20-60 minutes depending on your hardware."
echo "Memory requirement: ~6GB RAM"
echo ""
echo "Command: $PYPY_CMD ../../rpython/bin/rpython -O2 --sandbox targetpypystandalone.py"
echo ""

# Run translation
$PYPY_CMD ../../rpython/bin/rpython -O2 --sandbox targetpypystandalone.py

echo ""
echo "=== Build Complete ==="
echo ""

# Find the built executable
EXECUTABLE=$(ls -1 pypy3*-c 2>/dev/null | head -1 || true)
if [ -n "${EXECUTABLE}" ]; then
    echo "Sandboxed executable created: ${PYPY_ROOT}/pypy/goal/${EXECUTABLE}"
    echo ""
    echo "To run the sandboxed interpreter, you need the sandboxlib tools:"
    echo "  https://foss.heptapod.net/pypy/sandboxlib"
else
    echo "WARNING: Could not find built executable"
    echo "Check the pypy/goal directory for pypy3*-c files"
fi
