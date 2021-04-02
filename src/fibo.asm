org 0C00h
jmp loader

loader_msg:
    db 0Ah, "Starting loading the Fibonacci program...", 0Ah, "$"

loader:
    push b

    mov a, 3
    mov b, 1
    mov h, (loader_msg >> 8)
    mov l, (loader_msg & 255)
    int 4h

    xor a, a
    int 7h      ; reset storage system to copy

    mov a, 2    ; read the second sector to RAM
    pop b       ; storage number
    mov c, 2    ; count of sectors to read
    mov d, 0
    mov e, 1
    mov h, 0Dh
    mov l, 00h
    int 7h

    jmp start

padding:
    ; db 176 dup 0    ; pad
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
signature:
    db 0ABh         ; boot signature

intro:
    db 0Ah, "Enter the desired Fibo number (2 to 47): ", "$"

num_a equ 0C80h
num_b equ 0C84h
kb_buf equ 0C88h
KB_BUF_SIZE equ 16

SETUP proc
        mov c, (16 + KB_BUF_SIZE)
        xor a, a    ; (A)=0

        mov h, (num_a >> 8)
        mov l, (num_a & 255)
    set_loop:
        mov mem, a
        inc l
        dec c
        jnz set_loop

        mov l, (num_b & 255)
        mov mem, 01h    ; num_b = 1
        mov l, (kb_buf & 255)
        mov mem, KB_BUF_SIZE    ; set buffer max size

        ret
SETUP endp

DIG_TO_HEX proc
    ; (A) - digit to convert from num to HEX ASCII
        cmp a, 10
        jnc hex_conv_alpha  ; a >= 10
    hex_conv_dig:
        add a, '0'  ; a < 10
        jmp hex_conv
    hex_conv_alpha: ; a >= 10
        sub a, 10
        add a, 'A'
    hex_conv:
        ret
DIG_TO_HEX endp

PRINT_HEX proc
    ; (H)(L) - address of number
    ; (E) - number of bytes

        mov a, mem
        mov d, 0    ; cnt of digits
        mov b, 10

    hex_prep:
        mov c, 0    ; remainder

    hex_loop:
        sub a, 16   ; eq div by 16
        jc hex_save_ord
        inc c
        jmp hex_loop

    hex_save_ord:
        add a, 16   ; return digit to positive

        call DIG_TO_HEX
        push a  ; save digit
        inc d

        mov a, c
        cmp a, 16
        jnc hex_prep    ; jmp if remainder >= 16

        call DIG_TO_HEX
        push a  ; save digit
        inc d

        dec e
        jz hex_print_loop
        inc l
        jnz hex1
        inc h
    hex1:
        mov a, mem
        jmp hex_prep

    hex_print_loop:
        pop b
        mov a, 1
        mov c, 1
        int 4h
        dec d
        jnz hex_print_loop

        ret
PRINT_HEX endp

ADD_UI32 proc
    ; Realization the next sequence:
    ;     t = a + b
    ;     a = b
    ;     b = t
    ; or short:
    ;     a, b = b, a + b
    add_start:
        push a
        push b
        push c
        push d
        push e

        clc     ; clear carry flag
        mov c, 04h  ; counter for 32bit numbers
        mov h, (num_a >> 8) ; constant value

        mov d, (num_a & 255)
        mov e, (num_b & 255)

    add_loop:
        mov l, e
        mov a, mem  ; t = b
        mov b, mem  ; tb = b
        mov l, d
        adc a, mem  ; t = t(b) + a
        mov mem, b  ; a = tb(b)
        mov l, e
        mov mem, a  ; b = t

        inc d
        inc e
        dec c
        jnz add_loop

    add_end:
        pop e
        pop d
        pop c
        pop b
        pop a

        ret
ADD_UI32 endp

putc proc
    ; (B) Char to write
    push a
    push c

    mov a, 1
    mov c, 1
    int 4h

    pop c
    pop a

    ret
putc endp

put_nl proc
    mov b, 0Ah
    call putc   ; new line
    ret
put_nl endp

atoi proc
    ; (H)(L) - address of string buffer by INT5
    ; The string must contain only ASCII digits!
    ; (A) - result return
        push b
        push c
        push d
        push e

    atoi0:
        mov e, 0    ; result
        inc l
        jnz atoi1
        inc h

    atoi1:
        mov c, mem  ; string length
    atoi1_loop:
        inc l
        jnz atoi2
        inc h

    atoi2:
        mov a, mem
        sub a, '0'
        mov b, a

        xor a, a
        mov d, 10
    atoi3_mult:
        add a, e
        dec d
        jnz atoi3_mult   ; multiple by 10

        add a, b
        mov e, a    ; save result

    atoi4:
        dec c
        jnz atoi1_loop

    atoi_end:
        mov a, e
        pop e
        pop d
        pop c
        pop b

        ret
atoi endp

start:
    call SETUP

    mov a, 3
    mov b, 1
    mov h, (intro >> 8)
    mov l, (intro & 255)
    int 4h  ; print intro string

    ; get desired fibo number (2 to 47) (int5 A=4, clear buffer before (A=12))
    mov a, 0Ch
    mov b, 4
    mov h, (kb_buf >> 8)
    mov l, (kb_buf & 255)
    int 5h

    mov h, (kb_buf >> 8)
    mov l, (kb_buf & 255)
    call atoi
    mov c, a
    dec c

fibo:
    call ADD_UI32

    mov b, '.'
    call putc   ; put dot for each set

    dec c
    jnz fibo

    call put_nl ; new line

result:
    mov h, (num_b >> 8)
    mov l, (num_b & 255)

    mov b, "0"
    call putc
    mov b, "x"
    call putc

    mov e, 4
    call PRINT_HEX

    call put_nl ; new line

    jmp start

    hlt
