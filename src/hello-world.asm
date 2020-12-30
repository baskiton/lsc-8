org 0C00h
jmp start

hello:
    db 'Hello, World', 0Ah
msg:
    db "Printed from removable storage", 0Ah, '$'

start:
    mov a, 3    ; write string
    mov b, 0    ; by lenght
    mov c, (msg - hello)    ; len
    mov h, (hello >> 8)     ; string high address
    mov l, (hello & 255)    ; string low address
    int 4h      ; video interrupt

    mov a, 3    ; write string
    mov b, 1    ; up to terminal symbol '$'
    mov h, (msg >> 8)
    mov l, (msg & 255)
    int 4h      ; video interrupt

    hlt         ; halt system

db 184 dup 0    ; pad
db 0ABh         ; boot signature
