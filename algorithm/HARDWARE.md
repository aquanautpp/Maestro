# Hardware - Maestro Pi Zero

## Lista de Compras

| Item | Modelo | Preço | Link |
|------|--------|-------|------|
| Computador | Raspberry Pi Zero 2 W | $15 | [Aliexpress](https://aliexpress.com/w/wholesale-pi-zero-2-w.html) |
| Microfone | USB ou INMP441 | $5-10 | Aliexpress |
| Motor | Vibracall 3V (celular) | $0.50 | Aliexpress |
| Transistor | 2N2222 | $0.10 | Aliexpress |
| Resistor | 1K ohm | $0.01 | Aliexpress |
| Bateria | Powerbank USB 5000mAh | $10 | Qualquer |
| Cartão SD | 8GB+ | $5 | Qualquer |
| **Total** | | **~$35-40** | |

## Conexões

### Opção 1: Microfone USB (mais fácil)

```
Pi Zero 2 W
┌─────────────────────────────┐
│  USB ──── Microfone USB     │
│                             │
│  GPIO 17 ─┬── Motor (+)     │
│           R                 │
│           │                 │
│           └── 2N2222 Base   │
│                   │         │
│  GND ─────────────┴── Motor (-)
│                       2N2222 Emitter
│                             │
│  5V ──── Powerbank          │
└─────────────────────────────┘
```

Só pluga o microfone USB e funciona.

### Opção 2: INMP441 (menor, mais pro)

```
Pi Zero 2 W              INMP441
┌─────────────┐         ┌────────┐
│ 3.3V    ────┼─────────┤ VDD    │
│ GND     ────┼─────────┤ GND    │
│ GPIO 18 ────┼─────────┤ BCLK   │  (I2S Clock)
│ GPIO 19 ────┼─────────┤ LRCLK  │  (Word Select)
│ GPIO 20 ────┼─────────┤ DOUT   │  (Data)
│             │         │ L/R────┼── GND (Left channel)
└─────────────┘         └────────┘
```

Precisa habilitar I2S no Pi (o setup_pi.sh faz isso).

## Circuito do Motor

O GPIO do Pi fornece 3.3V e pouca corrente. O motor precisa de mais.
Usamos um transistor como "interruptor":

```
GPIO 17 ────[1K]────┐
                    │
                   Base
                    │
              ┌─────┴─────┐
     Motor    │  2N2222   │
    (+) ──────┤Collector  │
              │           │
              │  Emitter  │
              └─────┬─────┘
                    │
                   GND

Motor (-) ──── 3.3V ou 5V (dependendo do motor)
```

**Versão simplificada:** Se o motor for pequeno (tipo celular),
pode ligar direto no GPIO 17 sem transistor. Funciona, mas
não é o ideal.

## Foto do Protótipo

```
    ┌──────────────────────┐
    │    Pi Zero 2 W       │
    │  ┌────┐              │
    │  │USB │◄── Microfone │
    │  └────┘              │
    │         [GPIO 17]────┼──► Motor (no bolso/pulseira)
    │                      │
    │  ┌────┐              │
    │  │USB │◄── Powerbank │
    │  └────┘              │
    └──────────────────────┘
```

## Montagem Física (sugestões)

### Para teste em casa
- Pi + bateria numa pochete
- Motor no bolso da camisa (perto do corpo)
- Funciona sem case

### Para teste com famílias
- Case impresso 3D ou caixinha de plástico
- Velcro para prender no cinto/bolso
- Motor pode ficar junto ou em pulseira separada

### Produto final (futuro)
- PCB customizada
- ESP32-S3 (menor, menos bateria)
- Tudo numa pulseira

## Testando

1. **Testar motor:**
```bash
python3 pi_detector.py --test-vibrate
```

2. **Testar microfone:**
```bash
arecord -d 3 teste.wav && aplay teste.wav
```

3. **Testar tudo:**
```bash
python3 pi_detector.py
# Fale com voz aguda (criança)
# Espere 5 segundos
# Motor deve vibrar
```
