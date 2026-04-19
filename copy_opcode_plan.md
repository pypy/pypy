# Plan B — Add `COPY N` opcode to PyPy for 1:1 CPython 3.11 parity

## Motivation

Plan A (generalize `cleanup_end`) fixes the specific `sys.exc_info` leak but
leaves PyPy's bytecode divergent from CPython. Divergence has real cost:

- `dis.dis` output on PyPy doesn't match CPython's (already seen: exception
  table byte order was wrong, visible because our bytes are inspected by
  stdlib's `dis.py`).
- Tools that ship with `.pyc` files, bytecode rewriters (coverage, hypothesis,
  some JIT-assist libs), and users copy-pasting CPython disassembly examples
  break on PyPy.
- Every time we hand-code a workaround pattern (e.g. `PUSH_EXC_INFO; STORE
  None; DEL name; RERAISE 1` in place of `COPY 3; POP_EXCEPT; RERAISE 1`) we
  carry ongoing risk that the workaround is subtly wrong — exactly the class
  of bug we are currently debugging.

The cleanup-handler case is not the last divergence. Related missing
CPython 3.11 ops include `SWAP N`, possibly `COPY_FREE_VARS`, and a handful of
others Phase 1 of `exceptiontable.md` skipped. Adding the stack-shuffling ops
first ("`COPY N` + `SWAP N`") unblocks a whole family of future codegen
simplifications.

## Scope of this plan

Add `COPY N` (opcode 38) as a real opcode. Emit it
from codegen in the cleanup block between nested except handlers. Do NOT
touch the other divergent ops in the same PR — do them in follow-ups.

The companion question "also add `SWAP N`?" is listed in the follow-ups
section.

## Semantics

`COPY N` (arg `N`, 1-indexed): push a copy of the N-th stack element from the
top. I.e. `STACK[-N]` gets duplicated onto the top. Stack effect: +1.

- `COPY 1` is equivalent to `DUP_TOP`.
- `COPY 2` pushes a copy of the element just below TOS.
- `COPY 3` pushes a copy of the third-from-top element — this is what the
  except cleanup block uses.

Source of truth: `~/oss/cpython/Python/ceval.c` `TARGET(COPY)`.

## Implementation checklist

### 1. Opcode tables

- `pypy/tool/opcode3.py`: add `def_op('COPY', 38)`
- `pypy/interpreter/astcompiler/ops.py` (or wherever `ops.PUSH_EXC_INFO` is
  defined): add `COPY = 38`.

### 2. Stack effect

- `pypy/interpreter/astcompiler/assemble.py`:
  - If `COPY` is unconditionally +1, add to `_static_opcode_stack_effects`.
  - If stack effect depends on argument (it doesn't for `COPY` — always +1),
    handle in the dynamic switch instead. `COPY` is the static case: always
    `+1` regardless of `N`.
  - CPython's `stack_effect` (`Python/compile.c`) returns 1 for `COPY`.

### 3. Interpreter implementation

- `pypy/interpreter/pyopcode.py`: add the `COPY` handler.
  Sketch: `self.pushvalue(self.peekvalue(arg - 1))` (confirm the off-by-one
  against `peekvalue`'s indexing convention — PyPy uses 0-based where
  `peekvalue(0) == TOS`, so `COPY N` is `peekvalue(N - 1)`).
- Add `COPY` to the big opcode dispatch (the `cmp_ops` / `unrolling_opcodes`
  table in pyopcode.py) so both untranslated and translated execution see it.
- Check whether PyPy generates a compiled dispatch table from `opcode3.py`
  automatically or whether the opcode must be listed in a second place
  (historically the JIT needs entries in `pypy/module/pypyjit/interp_jit.py`
  or similar — confirm by grep'ping where `PUSH_EXC_INFO` is listed).

### 4. JIT support

- `pypy/module/pypyjit/`: check whether the JIT blacklists unknown opcodes or
  traces them. For a pure stack-shuffle `COPY N` should be trivially
  JIT-traceable (same class as `DUP_TOP`). Grep for `DUP_TOP` in `pypy/jit/`
  and mirror its treatment.
- Confirm `rpython/jit/metainterp`'s bytecode dispatcher handles unknown ops
  with a fallthrough or requires explicit entry.

### 5. Marshal / pyc

- Bump bytecode magic (already bumped on this branch to 432; confirm we don't
  need another bump). Since we're adding an opcode, any `.pyc` compiled with
  the new PyPy will not load on any other Python, but the magic already
  differs. No extra bump needed unless we want to version-track within PyPy
  history.

### 6. Codegen — use `COPY 3` in the except cleanup

- `pypy/interpreter/astcompiler/codegen.py::_visit_try_except`:
  - Replace the `as name` cleanup (lines 1019–1026) with the CPython shape:
    `COPY 3; POP_EXCEPT; RERAISE 1` for the cleanup_end block. Name-cleanup
    (`STORE None; DEL name`) stays, but now around the CPython-shaped core.
  - Generalize to bare `except T:` (lines 1027–1035): emit the same
    cleanup_end layout, without name-cleanup ops. This is where Plan A and
    Plan B converge — the fix to the `sys.exc_info` bug is the same user-
    visible change, differing only in what opcodes implement the cleanup.

### 6.5. Fine-grained with exception-table entries

Currently `_label_exception_targets` in `assemble.py` derives a single coarse
exception-table entry per with-statement, spanning everything from
`SETUP_WITH` to `POP_BLOCK`. CPython emits finer-grained entries split at
natural boundaries (body, inner `call_exit_with_nones`, `cleanup`→
`with_cleanup`, `exit2`'s trailing POP_TOP, etc.), each with its own depth
and handler.

Why do this between step 6 and step 7:
- Step 7's `dis.dis` / exception-table round-trip against CPython will
  otherwise show a long list of table-byte mismatches that are hard to
  triage; fixing ranges first turns step 7 into verification.
- Closes the `test_context_with_suppressed`-class of bugs: the recent fix
  (dropping SETUP_EXCEPT placeholder pushes) was a narrow correctness
  patch; fine-grained ranges remove the whole hazard — the outer with's
  own `call_exit_with_nones` gets its own entry pointing to the outer
  handler (CPython's `122 to 144 -> 194 [1]` pattern), instead of being
  accidentally covered by the inner body range.
- Unblocks step 10 cleanup: once ranges are explicit, `POP_BLOCK` has no
  compile-time role and `SETUP_WITH`'s range-marker use disappears —
  removing those dummy opcodes becomes safe.

Scope:
- Delete `_label_exception_targets` (assemble.py:761-809).
- In `handle_withitem` (codegen.py:1547-1640) emit explicit
  `emit_exception_table_entry` calls for each region matching CPython's
  boundaries.
- `POP_BLOCK` stays as a runtime no-op for now; `SETUP_WITH` unchanged.
- No opcode renumbering, no JIT work, no `BEFORE_WITH` migration.

Tests:
- Full `pypy/interpreter/test/` must still pass.
- `dis.dis` comparison (same apptest pattern used in step 6 debugging) of
  nested with over CPython 3.11 shows matching exception tables.

### 7. `dis.dis` / exception table display

- Verify `lib-python/3/dis.py` already knows `COPY` (it does — shipped with
  CPython 3.11 stdlib). Our `_parse_exception_table` was already fixed to
  big-endian, so `dis.dis` output should now round-trip with CPython's.

### 8. Tests

- `pypy/interpreter/astcompiler/test/test_assemble.py`: add a smoke test that
  `COPY 3` is encoded as byte 120 with arg 3.
- `pypy/interpreter/test/apptest_exceptions.py`:
  - `test_sys_exc_info_finally_nested` (already in tree) — must pass.
  - new twin: `except E as name:` version — must pass.
  - new twin: inside `with` — must pass.
- New app-level `test_copy_opcode.py` (via `compile()` or `exec`) that
  constructs a code object manually using `COPY 2` / `COPY 3` to exercise the
  opcode directly, independent of codegen.
- `lib-python/3/test/test_dis.py` and `test_code.py` — run full suite to
  check no regression in disassembly format.
- The three buildbot leak tests — must pass.

### 9. Translation / cross-checks

- Translate PyPy with the new opcode and run:
  - `lib-python/3/test/test_dis.py` — baseline `dis.dis` parity.
  - `lib-python/3/test/test_sys_settrace.py` — trace must still see sane
    events around the new cleanup.
  - `lib-python/3/test/test_exceptions.py` — broad exception coverage.
- Benchmark: measure microbenchmark of nested try/except raise/catch. No
  regression expected (replacing 4 opcodes with 3 opcodes).

### 10. Cleanup

- Renumber COPY to 120 like CPython and remove unused opcodes.

## Risk and rollback

- Risk: missing a dispatch table entry causes interpreter-level `KeyError` on
  `ops.COPY` or translation failure. Caught quickly by step 8's manual
  `COPY 2` test.
- Risk: JIT blacklists the new opcode and silently bails out of a trace.
  Caught by a JIT trace log on `test_raising_callback` after the fix.
- Rollback: Plan A is a strict subset of Plan B's codegen change (same
  table-entry shape, different cleanup body). If Plan B proves painful we
  can land the codegen half as Plan A, using the existing
  `PUSH_EXC_INFO; …; RERAISE 1` workaround pattern.

## Follow-ups (out of scope for this plan, but enabled by it)

- `SWAP N` (opcode 99) — CPython 3.11 uses it in match/case lowering and
  several new constructs. Same pattern as `COPY N`.
- Audit other hand-rolled stack-shuffle patterns in `codegen.py` that could
  be collapsed now that `COPY N` is available (e.g. the `except*` machinery
  at lines 1107–1150 already references "COPY 1" in comments — it's using
  `DUP_TOP` today, and those could be unified).
- Remove the `DUP_TOP`/`DUP_TOP_TWO`/`ROT_*` ops entirely in a future phase
  once codegen is fully translated to `COPY N`/`SWAP N` — matches CPython
  3.12+ direction.

## Choosing between Plan A and Plan B

Plan A: faster, surgical, no new opcode.
Plan B: more work up front, but:
- closes a known class of divergence bugs (not just this one)
- makes future CPython-3.12/3.13 compatibility work cheaper
- makes `dis.dis` output byte-for-byte match CPython, helping third-party tools
- is more in the spirit of the exceptiontable branch's overall goal
  (CPython 3.11 compatibility of the exception model)

Recommendation: default to Plan B unless a blocking issue appears in step 4
(JIT support) or step 5 (pyc magic interaction with other in-flight work).

## We chose Plan B

Status: completed steps 1,2,3,4,5,6. Next: step 6.5 (fine-grained with
exception-table entries), then step 7.
