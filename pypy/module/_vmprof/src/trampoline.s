	.text
    .p2align 4,,-1
	.globl	pypy_execute_frame_trampoline
	.type	pypy_execute_frame_trampoline, @function
pypy_execute_frame_trampoline:
	.cfi_startproc
    pushq   %rdi
	.cfi_def_cfa_offset 16
    movabs  $pypy_pyframe_execute_frame, %rax
	callq	*%rax
    popq    %rdi
	.cfi_def_cfa_offset 8
    ret
	.cfi_endproc
	.size	pypy_execute_frame_trampoline, .-pypy_execute_frame_trampoline
