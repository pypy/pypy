# Step 6 — CPython byte-for-byte parity for exception cleanup

Goal: rewrite PyPy's exception-dispatch runtime and codegen so that the
bytecode emitted for `try/except`, `try/finally`, `with`, and async variants
matches CPython 3.11 instruction-for-instruction.  After this step, `dis.dis`
output on PyPy equals CPython's.

## Current status (2026-04-18)

**Semantic parity achieved** for the exception-table contract.  **Byte-for-byte
`dis.dis` parity not achieved** — out-of-scope opcode-shape differences remain
(see "Remaining differences" below).

Done:
- `handle_operation_error` pushes `lasti` + exc for `lasti=True` handlers;
  `_reraise_saved_lasti` replaced with transient `_reraise_lasti` field
  (pyopcode.py:121-198).
- `RERAISE N` reads lasti from `PEEK(N+1)`, updates transient `_reraise_lasti`
  for next dispatch, does NOT touch `sys.exc_info` (pyopcode.py:1357+).
- `POP_EXCEPT` unchanged; always precedes `RERAISE 1` in outer cleanups.
- Cleanup pattern `COPY N; POP_EXCEPT; RERAISE 1` emitted at every site:
  except-as inner/outer (codegen.py:1028-1032), bare-except, try/finally
  (codegen.py:1146), with (codegen.py:1629-1634), async-for-in-async-with
  (codegen.py:896 — ROT_THREE; POP_EXCEPT; POP_TOP; RERAISE 0 to match
  aiter-drop semantics).
- Exception-table entries carry correct `depth` + `lasti`; depth derivation
  in `_build_exceptiontable` uses `-2` for lasti, `-1` otherwise
  (assemble.py:855-857).
- `_label_exception_targets` only tracks `SETUP_WITH` / `SETUP_ASYNC_WITH`
  (the only opcodes with matching `POP_BLOCK`); `SETUP_FINALLY` /
  `SETUP_EXCEPT` are compile-time dummies and do not participate in the
  handler-stack pairing (assemble.py:771-809).  This fix closed the
  `test_context_with_suppressed` nested-with bug.
- `duplicate_exits_without_lineno` skips RERAISE-only targets to avoid
  corrupting exception-table ranges (assemble.py:961).
- Full `pypy/interpreter/test/` suite: 1276 passed, 18 skipped, 0 failures
  (untranslated PyPy).

Remaining differences (`dis.dis` parity — deferred to later steps):
- Dummy `SETUP_FINALLY` / `SETUP_EXCEPT` / `POP_BLOCK` opcodes still emitted
  (runtime no-ops; used for `_stacksize` seeding and with-range delimiting).
- Call sequence: PyPy `CALL_FUNCTION` vs CPython `PUSH_NULL; …; PRECALL; CALL`
  with inline caches.
- With-entry: PyPy `SETUP_WITH` vs CPython `BEFORE_WITH` (and different
  __exit__ push sequence upstream).
- `DUP_TOP` / `DUP_TOP_TWO` vs CPython `COPY 1` / `COPY 2`.
- `LOAD_GLOBAL` without the NULL-push bit.
- `LOAD_METHOD` + `CALL_METHOD` vs CPython `LOAD_ATTR` + `PRECALL`.
- Unified `POP_JUMP_IF_TRUE` / `_FALSE` vs CPython's directional variants.

Deferred to step 6.5 (see `copy_opcode_plan.md`):
- Coarser with-range exception-table entries — PyPy currently derives a
  single range per with from `SETUP_WITH`..`POP_BLOCK` in
  `_label_exception_targets`; CPython splits at natural boundaries (body,
  inner `call_exit_with_nones`, `cleanup`→`with_cleanup`, `exit2` trailing
  POP_TOP, etc.).  This is closer to a correctness/cleanup task than an
  opcode-shape task: it removes the `test_context_with_suppressed`-class
  hazard entirely and is a prerequisite for cleanly dropping `POP_BLOCK`
  in step 10.

Runtime-behavior note: PyPy's `call_valuestack` speed hack
(function.py:139) drops args *before* calling, so on an exception the
caller's stack slots are None where CPython's would still hold args/func.
`handle_operation_error`'s `dropvaluesuntil` masks this as long as the
compiler picks handler depths matching PyPy's post-drop stack.  The
`test_context_with_suppressed` bug was exactly a mismatch here.

## Core semantic change

**Before (PyPy):**
- `handle_operation_error` pops to `depth`, pushes `new_exc`.  Stack:
  `[..., prev_exc, new_exc]`.
- `_reraise_saved_lasti` frame field holds the original raise offset.
- `RERAISE 1`: pops `new_exc`, pops `prev_exc`, restores `sys.exc_info` from
  `prev_exc`, reraises using `_reraise_saved_lasti`.
- `RERAISE 0`: pops `new_exc`, reraises.

**After (CPython parity):**
- `handle_operation_error` pops to `depth`; if the exception table entry has
  `lasti=True`, pushes `intmask(self.last_instr)` as an integer; then pushes
  `new_exc`.  Stack: `[..., prev_exc, lasti, new_exc]` for lasti-flagged
  handlers, `[..., prev_exc, new_exc]` otherwise.
- No `_reraise_saved_lasti` field.
- `RERAISE 1`: reads `lasti` from `PEEK(2)`, sets `self.last_instr = lasti`,
  pops `new_exc`, reraises.  No `sys.exc_info` restore, no `prev_exc` pop.
- `RERAISE 0`: unchanged — pops `new_exc`, reraises.
- `POP_EXCEPT`: unchanged — pops TOS, restores `sys.exc_info` from it.

## Cleanup shape (matches CPython)

For `except E as name:`:

```
handler:                     # stack: [prev, exc] (from PUSH_EXC_INFO + match)
   PUSH_EXC_INFO
   LOAD type; CHECK_EXC_MATCH; POP_JUMP_IF_FALSE no_match
   STORE name                # stack: [prev]
   <body>                    # table entry body -> inner_cleanup, lasti=True
   POP_EXCEPT; LOAD None; STORE name; DEL name; JUMP_FORWARD end

no_match:                    # stack: [prev, lasti, exc]
   RERAISE 0                 # pops exc, reraises; caught by outer_cleanup

inner_cleanup:               # stack: [prev, lasti, exc]  (body raised)
   LOAD None; STORE name; DEL name
   RERAISE 1                 # reads lasti, pops exc, reraises

outer_cleanup:               # stack: [prev, lasti, exc]  (inner/no_match reraised)
   COPY 3                    # push copy of prev
   POP_EXCEPT                # pop prev copy, restore exc_info
   RERAISE 1                 # reads lasti, pops exc, reraises upward
```

Exception table entries for this region:
- `<body>` range -> `inner_cleanup`  depth=D+1 (prev on stack)  lasti=True
- `inner_cleanup` + `no_match` range -> `outer_cleanup`  depth=D+1  lasti=True

For bare `except T:`: same shape, without the `LOAD None; STORE name; DEL name`
in either cleanup block.

For `try/finally`, `with`, async-for-in-async-with: each RERAISE 1 emission
becomes `COPY N; POP_EXCEPT; RERAISE 1` with N chosen to match the stack
depth of `prev_exc` at that point.  N = (extra non-prev items on stack) + 3.
For plain `[prev, lasti, exc]`, N=3.  For with-body `[__exit__, prev, lasti,
exc]`, N=4.

## RERAISE 1 emission sites (from grep)

1. `codegen.py:896` async-for in async-with no-StopAsyncIteration branch
   - Stack: `[aiter, prev, lasti, exc]` once table entry made lasti=True
   - Change: `COPY 4; POP_EXCEPT; RERAISE 1`
   - Must also change the covering table entry at `codegen.py:851` to
     `lasti=True`.

2. `codegen.py:1027` except-as inner cleanup
   - Stack: `[prev, lasti, exc]`
   - Change: current `LOAD None; STORE name; DEL name; RERAISE 1` stays as
     inner cleanup.  Add new outer_cleanup emitting
     `COPY 3; POP_EXCEPT; RERAISE 1` and table entry covering inner cleanup
     + no_match range.

3. `codegen.py:1063` bare-except inner cleanup
   - Stack: `[prev, lasti, exc]`
   - Change: `RERAISE 1` stays as inner.  Add outer_cleanup with
     `COPY 3; POP_EXCEPT; RERAISE 1`.

4. `codegen.py:1070` no-match fallthrough after all handlers
   - Stack: `[prev, lasti, exc]`
   - Change: `RERAISE 1` -> `RERAISE 0`.  Outer cleanups from #2/#3 catch it.

5. `codegen.py:1117` try/finally exceptional body end
   - Stack after finally body: `[prev, lasti, exc]`
   - Change: `COPY 3; POP_EXCEPT; RERAISE 1` (wait — CPython actually emits
     this differently; verify once we have disassembly).  Current table entry
     at 1089 is `emit_exception_table_entry(body, end, end_block=...)` —
     confirm lasti.

6. `codegen.py:1581` with __exit__-false path after WITH_EXCEPT_START
   - Stack: `[__exit__, prev, lasti, exc]` (once table entry is lasti=True)
   - Change: `COPY 4; POP_EXCEPT; RERAISE 1`
   - Table entry for with-cleanup (line 1582) must become lasti=True.

7. `codegen.py:1585` with_cleanup secondary
   - Stack, table entry: need re-examination.

8. `codegen.py:1294` try-except-star reraise path
   - Currently `RERAISE` (arg 0).  Leave as-is unless audit says otherwise.

## Runtime files touched

- `pypy/interpreter/pyopcode.py`
  - `handle_operation_error` (lines 121-187): push lasti, drop
    `_reraise_saved_lasti` logic (lines 153-160, 175-179).
  - `RERAISE` (lines 1347-1365): new semantics.
  - `_reraise_saved_lasti` init (line 819): delete.
- `pypy/interpreter/pyframe.py`
  - `_reraise_saved_lasti` field (line 78): delete.
  - `mark_stacks` (line 903): add `_MS_LASTI` kind; on lasti=True handler
    dispatch, seed `[..., prev, lasti, exc]`; comment at line 1045 updated.
- `pypy/interpreter/astcompiler/assemble.py`
  - Exception-table depth calc (line 856): `-2` if lasti else `-1`.
  - `_opcode_stack_effect` uses `_static_opcode_stack_effects` for known
    opcodes; no change needed for COPY (already +1) or RERAISE (already -1).

## Codegen changes

All sites above.  New helper `emit_outer_cleanup(prev_depth_from_tos)` that
emits `COPY N; POP_EXCEPT; RERAISE 1` with the right N.

## Tests

- `pypy/interpreter/test/apptest_exceptions.py` — must still pass without
  changes (they pass on CPython; our new bytecode is CPython-parity).
- `pypy/interpreter/astcompiler/test/apptest_exceptiongroup.py` — same.
- The three buildbot leak tests.
- Final: `dis.dis` comparison against CPython 3.11 on a representative
  exception-handling snippet.

## Risk log

- `mark_stacks` needs `_MS_LASTI`, else `fset_f_lineno` validation breaks
  whenever jump crosses a lasti-on-stack region.
- Depth calc `-2` in assembler must agree with runtime push count.
- Any RERAISE 1 left pointing at a handler whose table entry is `lasti=False`
  will read garbage from PEEK(2).  Every RERAISE 1 emit site must match a
  lasti=True covering table entry.
- Traceback entry at RERAISE site: CPython `RERAISE` uses `attach_tb=False`
  equivalent (it sets prev_instr from the lasti read).  PyPy already passes
  `attach_tb=False` via `RaiseWithExplicitTraceback`; keep that.

## Out of scope for this commit

- Opcode renumbering (step 10 — COPY=38 -> 120).
- Removing DUP_TOP/ROT_* (future work).
- SWAP N (follow-up).
