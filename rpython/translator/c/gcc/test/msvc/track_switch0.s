; Function compile flags: /Odtpy
;	COMDAT _pypy_g_BuiltinActivation_UwS_UCD_ObjSpace_W_Root_W_Root
_TEXT	SEGMENT
tv138 = -116						; size = 4
_l_v271568$ = -109					; size = 1
_l_v271567$ = -108					; size = 4
_l_v271575$ = -104					; size = 4
_l_v271551$ = -97					; size = 1
_l_v271579$ = -96					; size = 4
_l_v271576$ = -89					; size = 1
_l_v271572$ = -88					; size = 4
_l_v271583$ = -84					; size = 4
_l_v271556$ = -80					; size = 4
_l_v271559$ = -76					; size = 4
_l_v271544$ = -72					; size = 4
_l_v271545$ = -68					; size = 4
_l_v271580$ = -64					; size = 4
_l_v271557$ = -60					; size = 4
_l_v271581$ = -56					; size = 4
_l_v271553$ = -52					; size = 4
_l_v271570$ = -48					; size = 4
_l_v271554$ = -42					; size = 1
_l_v271565$ = -41					; size = 1
_l_v271558$ = -40					; size = 4
_l_v271562$ = -33					; size = 1
_l_v271561$ = -32					; size = 4
_l_v271547$ = -28					; size = 4
_l_v271548$ = -24					; size = 4
_l_v271573$ = -18					; size = 1
_l_v271546$ = -17					; size = 1
_l_v271582$ = -16					; size = 4
_l_v271550$ = -12					; size = 4
_l_v271564$ = -8					; size = 4
_l_v271578$ = -4					; size = 4
_l_self_596$ = 8					; size = 4
_l_scope_w_259$ = 12					; size = 4
_pypy_g_BuiltinActivation_UwS_UCD_ObjSpace_W_Root_W_Root PROC ; COMDAT

; 15629: struct pypy_pypy_interpreter_baseobjspace_W_Root0 *pypy_g_BuiltinActivation_UwS_UCD_ObjSpace_W_Root_W_Root(struct pypy_pypy_interpreter_gateway_BuiltinActivation0 *l_self_596, struct pypy_array1 *l_scope_w_259) {

	push	ebp
	mov	ebp, esp
	sub	esp, 116				; 00000074H
$block0$211591:

; 15630: 	bool_t l_v271551; bool_t l_v271554; bool_t l_v271562;
; 15631: 	bool_t l_v271565; bool_t l_v271568; bool_t l_v271573;
; 15632: 	bool_t l_v271576; char l_v271546; long l_v271550; long l_v271553;
; 15633: 	long l_v271564; long l_v271567; long l_v271572; long l_v271575;
; 15634: 	struct pypy_object0 *l_v271556; struct pypy_object0 *l_v271570;
; 15635: 	struct pypy_object0 *l_v271578;
; 15636: 	struct pypy_object_vtable0 *l_v271561;
; 15637: 	struct pypy_pypy_interpreter_baseobjspace_W_Root0 *l_v271544;
; 15638: 	struct pypy_pypy_interpreter_baseobjspace_W_Root0 *l_v271545;
; 15639: 	struct pypy_pypy_interpreter_baseobjspace_W_Root0 *l_v271557;
; 15640: 	struct pypy_pypy_interpreter_baseobjspace_W_Root0 *l_v271579;
; 15641: 	struct pypy_pypy_interpreter_baseobjspace_W_Root0 *l_v271580;
; 15642: 	struct pypy_pypy_interpreter_baseobjspace_W_Root0 *l_v271581;
; 15643: 	struct pypy_pypy_interpreter_baseobjspace_W_Root0 *l_v271582;
; 15644: 	struct pypy_pypy_interpreter_baseobjspace_W_Root0 *l_v271583;
; 15645: 	struct pypy_pypy_interpreter_gateway_BuiltinActivation_UwS_UCD0 *l_v271548;
; 15646: 	struct pypy_pypy_module_unicodedata_interp_ucd_UCD0 *l_v271547;
; 15647: 	void* l_v271558; void* l_v271559;
; 15648: 
; 15649:     block0:
; 15650: 	l_v271548 = (struct pypy_pypy_interpreter_gateway_BuiltinActivation_UwS_UCD0 *)l_self_596;

	mov	eax, DWORD PTR _l_self_596$[ebp]
	mov	DWORD PTR _l_v271548$[ebp], eax

; 15651: 	l_v271546 = RPyField(l_v271548, bausucdoswrwr_inst_behavior);

	mov	ecx, DWORD PTR _l_v271548$[ebp]
	mov	dl, BYTE PTR [ecx+8]
	mov	BYTE PTR _l_v271546$[ebp], dl

; 15652: 	RPyAssert(1, "unexpectedly negative list getitem index");
; 15653: 	l_v271550 = l_scope_w_259->length;

	mov	eax, DWORD PTR _l_scope_w_259$[ebp]
	mov	ecx, DWORD PTR [eax+4]
	mov	DWORD PTR _l_v271550$[ebp], ecx

; 15654: 	OP_INT_LT(0L, l_v271550, l_v271551);

	xor	edx, edx
	cmp	DWORD PTR _l_v271550$[ebp], 0
	setg	dl
	mov	BYTE PTR _l_v271551$[ebp], dl

; 15655: 	RPyAssert(l_v271551, "list getitem index out of bound");
; 15656: 	l_v271553 = l_scope_w_259->length;

	mov	eax, DWORD PTR _l_scope_w_259$[ebp]
	mov	ecx, DWORD PTR [eax+4]
	mov	DWORD PTR _l_v271553$[ebp], ecx

; 15657: 	OP_INT_LT(0L, l_v271553, l_v271554);

	xor	edx, edx
	cmp	DWORD PTR _l_v271553$[ebp], 0
	setg	dl
	mov	BYTE PTR _l_v271554$[ebp], dl

; 15658: 	RPyAssert(l_v271554, "fixed getitem out of bounds");
; 15659: 	l_v271556 = RPyItem(l_scope_w_259, 0L);

	mov	eax, DWORD PTR _l_scope_w_259$[ebp]
	mov	ecx, DWORD PTR [eax+8]
	mov	DWORD PTR _l_v271556$[ebp], ecx

; 15660: 	l_v271557 = (struct pypy_pypy_interpreter_baseobjspace_W_Root0 *)l_v271556;

	mov	edx, DWORD PTR _l_v271556$[ebp]
	mov	DWORD PTR _l_v271557$[ebp], edx

; 15661: 	l_v271547 = pypy_g_interp_w__UCD(l_v271557, 0);

	push	0
	mov	eax, DWORD PTR _l_v271557$[ebp]
	push	eax
	call	_pypy_g_interp_w__UCD
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | 12(%ebp)}
	add	esp, 8
	mov	DWORD PTR _l_v271547$[ebp], eax

; 15662: 	l_v271558 = (void*)l_scope_w_259;

	mov	ecx, DWORD PTR _l_scope_w_259$[ebp]
	mov	DWORD PTR _l_v271558$[ebp], ecx

; 15663: 	l_v271559 = pypy_asm_gcroot(l_v271558);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v271558$[ebp]
	mov	edx, DWORD PTR _l_v271558$[ebp]
	mov	DWORD PTR _l_v271559$[ebp], edx

; 15664: 	l_scope_w_259 = l_v271559; /* for moving GCs */

	mov	eax, DWORD PTR _l_v271559$[ebp]
	mov	DWORD PTR _l_scope_w_259$[ebp], eax

; 15665: 	l_v271561 = RPyField((&pypy_g_ExcData), ed_exc_type);

	mov	ecx, DWORD PTR _pypy_g_ExcData
	mov	DWORD PTR _l_v271561$[ebp], ecx

; 15666: 	l_v271562 = (l_v271561 == NULL);

	xor	edx, edx
	cmp	DWORD PTR _l_v271561$[ebp], 0
	sete	dl
	mov	BYTE PTR _l_v271562$[ebp], dl

; 15667: 	if (!l_v271562) {

	movzx	eax, BYTE PTR _l_v271562$[ebp]
	test	eax, eax
	jne	SHORT $block1$211600

; 15668: 		l_v271583 = ((struct pypy_pypy_interpreter_baseobjspace_W_Root0 *) NULL);

	mov	DWORD PTR _l_v271583$[ebp], 0

; 15669: 		goto block3;

	jmp	$block3$211599
$block1$211600:

; 15670: 	}
; 15671: 	goto block1;
; 15672: 
; 15673:     block1:
; 15674: 	RPyAssert(1, "unexpectedly negative list getitem index");
; 15675: 	l_v271564 = l_scope_w_259->length;

	mov	ecx, DWORD PTR _l_scope_w_259$[ebp]
	mov	edx, DWORD PTR [ecx+4]
	mov	DWORD PTR _l_v271564$[ebp], edx

; 15676: 	OP_INT_LT(1L, l_v271564, l_v271565);

	xor	eax, eax
	cmp	DWORD PTR _l_v271564$[ebp], 1
	setg	al
	mov	BYTE PTR _l_v271565$[ebp], al

; 15677: 	RPyAssert(l_v271565, "list getitem index out of bound");
; 15678: 	l_v271567 = l_scope_w_259->length;

	mov	ecx, DWORD PTR _l_scope_w_259$[ebp]
	mov	edx, DWORD PTR [ecx+4]
	mov	DWORD PTR _l_v271567$[ebp], edx

; 15679: 	OP_INT_LT(1L, l_v271567, l_v271568);

	xor	eax, eax
	cmp	DWORD PTR _l_v271567$[ebp], 1
	setg	al
	mov	BYTE PTR _l_v271568$[ebp], al

; 15680: 	RPyAssert(l_v271568, "fixed getitem out of bounds");
; 15681: 	l_v271570 = RPyItem(l_scope_w_259, 1L);

	mov	ecx, DWORD PTR _l_scope_w_259$[ebp]
	mov	edx, DWORD PTR [ecx+12]
	mov	DWORD PTR _l_v271570$[ebp], edx

; 15682: 	l_v271544 = (struct pypy_pypy_interpreter_baseobjspace_W_Root0 *)l_v271570;

	mov	eax, DWORD PTR _l_v271570$[ebp]
	mov	DWORD PTR _l_v271544$[ebp], eax

; 15683: 	RPyAssert(1, "unexpectedly negative list getitem index");
; 15684: 	l_v271572 = l_scope_w_259->length;

	mov	ecx, DWORD PTR _l_scope_w_259$[ebp]
	mov	edx, DWORD PTR [ecx+4]
	mov	DWORD PTR _l_v271572$[ebp], edx

; 15685: 	OP_INT_LT(2L, l_v271572, l_v271573);

	xor	eax, eax
	cmp	DWORD PTR _l_v271572$[ebp], 2
	setg	al
	mov	BYTE PTR _l_v271573$[ebp], al

; 15686: 	RPyAssert(l_v271573, "list getitem index out of bound");
; 15687: 	l_v271575 = l_scope_w_259->length;

	mov	ecx, DWORD PTR _l_scope_w_259$[ebp]
	mov	edx, DWORD PTR [ecx+4]
	mov	DWORD PTR _l_v271575$[ebp], edx

; 15688: 	OP_INT_LT(2L, l_v271575, l_v271576);

	xor	eax, eax
	cmp	DWORD PTR _l_v271575$[ebp], 2
	setg	al
	mov	BYTE PTR _l_v271576$[ebp], al

; 15689: 	RPyAssert(l_v271576, "fixed getitem out of bounds");
; 15690: 	l_v271578 = RPyItem(l_scope_w_259, 2L);

	mov	ecx, DWORD PTR _l_scope_w_259$[ebp]
	mov	edx, DWORD PTR [ecx+16]
	mov	DWORD PTR _l_v271578$[ebp], edx

; 15691: 	l_v271545 = (struct pypy_pypy_interpreter_baseobjspace_W_Root0 *)l_v271578;

	mov	eax, DWORD PTR _l_v271578$[ebp]
	mov	DWORD PTR _l_v271545$[ebp], eax

; 15692: 	switch (l_v271546) {

	movsx	ecx, BYTE PTR _l_v271546$[ebp]
	mov	DWORD PTR tv138[ebp], ecx
	cmp	DWORD PTR tv138[ebp], 3
	ja	SHORT $LN1@pypy_g_Bui@2
	mov	edx, DWORD PTR tv138[ebp]
	jmp	DWORD PTR $LN14@pypy_g_Bui@2[edx*4]
$LN5@pypy_g_Bui@2:

; 15693:     case 0:
; 15694: 		goto block2;

	jmp	SHORT $block2$211608
$LN4@pypy_g_Bui@2:

; 15695:     case 1:
; 15696: 		goto block4;

	jmp	SHORT $block4$211610
$LN3@pypy_g_Bui@2:

; 15697:     case 2:
; 15698: 		goto block5;

	jmp	SHORT $block5$211612
$LN2@pypy_g_Bui@2:

; 15699:     case 3:
; 15700: 		goto block6;

	jmp	$block6$211614
$LN1@pypy_g_Bui@2:

; 15701:     default:
; 15702: 		assert(!"bad switch!!");

	mov	eax, OFFSET ??_C@_0N@PGLFNKFI@bad?5switch?$CB?$CB?$AA@
	test	eax, eax
	je	SHORT $block2$211608
	push	15702					; 00003d56H
	push	OFFSET ??_C@_1BO@DMBFIACJ@?$AAi?$AAm?$AAp?$AAl?$AAe?$AAm?$AAe?$AAn?$AAt?$AA_?$AA1?$AA1?$AA?4?$AAc?$AA?$AA@
	push	OFFSET ??_C@_1CA@EIJBLFPJ@?$AA?$CB?$AA?$CC?$AAb?$AAa?$AAd?$AA?5?$AAs?$AAw?$AAi?$AAt?$AAc?$AAh?$AA?$CB?$AA?$CB?$AA?$CC?$AA?$AA@
	call	DWORD PTR __imp___wassert
	add	esp, 12					; 0000000cH
$block2$211608:

; 15703: 	}
; 15704: 
; 15705:     block2:
; 15706: 	l_v271579 = pypy_g_UCD_digit(l_v271547, l_v271544, l_v271545);

	mov	edx, DWORD PTR _l_v271545$[ebp]
	push	edx
	mov	eax, DWORD PTR _l_v271544$[ebp]
	push	eax
	mov	ecx, DWORD PTR _l_v271547$[ebp]
	push	ecx
	call	_pypy_g_UCD_digit
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	add	esp, 12					; 0000000cH
	mov	DWORD PTR _l_v271579$[ebp], eax

; 15707: 	l_v271583 = l_v271579;

	mov	edx, DWORD PTR _l_v271579$[ebp]
	mov	DWORD PTR _l_v271583$[ebp], edx
$block3$211599:

; 15708: 	goto block3;
; 15709: 
; 15710:     block3:
; 15711: 	RPY_DEBUG_RETURN();
; 15712: 	return l_v271583;

	mov	eax, DWORD PTR _l_v271583$[ebp]
	jmp	SHORT $LN9@pypy_g_Bui@2
$block4$211610:

; 15713: 
; 15714:     block4:
; 15715: 	l_v271580 = pypy_g_UCD_name(l_v271547, l_v271544, l_v271545);

	mov	eax, DWORD PTR _l_v271545$[ebp]
	push	eax
	mov	ecx, DWORD PTR _l_v271544$[ebp]
	push	ecx
	mov	edx, DWORD PTR _l_v271547$[ebp]
	push	edx
	call	_pypy_g_UCD_name
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	add	esp, 12					; 0000000cH
	mov	DWORD PTR _l_v271580$[ebp], eax

; 15716: 	l_v271583 = l_v271580;

	mov	eax, DWORD PTR _l_v271580$[ebp]
	mov	DWORD PTR _l_v271583$[ebp], eax

; 15717: 	goto block3;

	jmp	SHORT $block3$211599
$block5$211612:

; 15718: 
; 15719:     block5:
; 15720: 	l_v271581 = pypy_g_UCD_decimal(l_v271547, l_v271544, l_v271545);

	mov	ecx, DWORD PTR _l_v271545$[ebp]
	push	ecx
	mov	edx, DWORD PTR _l_v271544$[ebp]
	push	edx
	mov	eax, DWORD PTR _l_v271547$[ebp]
	push	eax
	call	_pypy_g_UCD_decimal
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	add	esp, 12					; 0000000cH
	mov	DWORD PTR _l_v271581$[ebp], eax

; 15721: 	l_v271583 = l_v271581;

	mov	ecx, DWORD PTR _l_v271581$[ebp]
	mov	DWORD PTR _l_v271583$[ebp], ecx

; 15722: 	goto block3;

	jmp	SHORT $block3$211599
$block6$211614:

; 15723: 
; 15724:     block6:
; 15725: 	l_v271582 = pypy_g_UCD_numeric(l_v271547, l_v271544, l_v271545);

	mov	edx, DWORD PTR _l_v271545$[ebp]
	push	edx
	mov	eax, DWORD PTR _l_v271544$[ebp]
	push	eax
	mov	ecx, DWORD PTR _l_v271547$[ebp]
	push	ecx
	call	_pypy_g_UCD_numeric
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	add	esp, 12					; 0000000cH
	mov	DWORD PTR _l_v271582$[ebp], eax

; 15726: 	l_v271583 = l_v271582;

	mov	edx, DWORD PTR _l_v271582$[ebp]
	mov	DWORD PTR _l_v271583$[ebp], edx

; 15727: 	goto block3;

	jmp	SHORT $block3$211599
$LN9@pypy_g_Bui@2:

; 15728: }

	mov	esp, ebp
	pop	ebp
	ret	0
	npad	3
$LN14@pypy_g_Bui@2:
	DD	$LN5@pypy_g_Bui@2
	DD	$LN4@pypy_g_Bui@2
	DD	$LN3@pypy_g_Bui@2
	DD	$LN2@pypy_g_Bui@2
_pypy_g_BuiltinActivation_UwS_UCD_ObjSpace_W_Root_W_Root ENDP
