# pyhdrdump

A clang-based tool that dumps the `Py`-prefixed API surface of a `Python.h`-style
header in a normalized form, so that CPython's and PyPy's headers can be diffed
to find where they disagree -- inline macro vs. real function, or mismatched
argument/return types (the "signed vs. long" class of ABI bugs).

This is a reconstruction of the (never-published) tool described by `nulano` in
[pypy/pypy#3397](https://github.com/pypy/pypy/issues/3397#issuecomment-1872091878).
It uses **libclang** rather than a preprocessed-source parser (e.g. pycparser)
because the whole point is to examine the `#define`s themselves *and* resolve
real C types at the same time -- something only a full compiler front end can do.

## What it emits

One line per reported name, sorted by name. Only names starting with `Py` (but
not `PyPy`) are reported.

* **Functions:** `RETTYPE NAME(ARGTYPE, ...)`, no parameter names.
* Typedef'd primitives are replaced by their underlying base type
  (`Py_ssize_t` -> `long` on LP64, `long long` on win64 -- this divergence is the
  point).
* A pointer to a struct/union/void/pointer/function becomes `void *`; a pointer
  to a primitive is kept (`const char *`, `long *`). The pointee's `const` is
  preserved.
* A macro that is a plain alias of, or a pure argument-forwarder to, a function
  is printed as that function under the macro's name, with the real name in a
  trailing comment:
  `long PyObject_Length(void *) /* macro, real name PyObject_Size */`.
* A macro that aliases another macro is printed with the fully expanded value
  and the real macro name in a comment.
* Every other macro is printed verbatim as `#define ...`.

## Build

Needs libclang and its dev headers (Debian/Ubuntu: `apt install libclang-18-dev`).
`build.sh`, `compare.sh` and the `pyhdrdump` binary all work from any directory;
the build resolves its source/output relative to the script, not the cwd.

```sh
sh pypy/tool/pyhdrdump/build.sh    # produces pypy/tool/pyhdrdump/pyhdrdump
# override the toolchain if needed:
LLVM_CONFIG=llvm-config-18 CXX=clang++-18 sh pypy/tool/pyhdrdump/build.sh
```

## Use

```sh
T=pypy/tool/pyhdrdump          # adjust to your checkout

# CPython (system dev headers)
$T/pyhdrdump /usr/include/python3.12/Python.h -I/usr/include/python3.12 > cpython312.dump

# PyPy: needs the *generated* cpyext headers (pypy_macros.h, pypy_decl.h,
# that a translation produces. On the py3.12 branch
# those live in include/pypy3.12 alongside the static headers. Make sure these
# match the branch you are comparing -- a stale 3.11 build dir will silently
# compare the wrong versions.
$T/pyhdrdump include/pypy3.12/Python.h -Iinclude/pypy3.12 > pypy312.dump

# categorised diff
sh $T/compare.sh cpython312.dump pypy312.dump
```

`compare.sh` strips PyPy's `/* macro, real name PyPy... */` aliasing noise (PyPy
exports nearly every function via such a macro) and reports only: (A) names that
are a `#define` in one header but a real function in the other, (B) functions
whose signatures differ, and (C) names present in only one header.

## Caveats

* Output is platform-specific by design (it reflects the target the header is
  parsed for). To reproduce nulano's win64 dumps, cross-parse with
  `--target=x86_64-pc-windows-msvc` and the matching headers.
* By-value structs are left as-is, so a struct declared anonymously in one header
  (`Py_complex`) and named in the other (`struct Py_complex_t`) show as different
  text though they are ABI-identical -- read those as "same".
* A `va_list` argument prints as the target's canonical spelling
  (`struct __va_list_tag[1]` on Linux, `char *` on win64); again a platform
  artifact, not a real divergence.
