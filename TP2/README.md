# Estructura del Proyecto

```
tp2_redes/
├── pox/                    # Carpeta de POX (controlador SDN)
│   ├── pox.py             # Ejecutable principal de POX
│   ├── firewall.py        # Módulo del firewall
│   └── pox/               # Módulos internos de POX
├── rules.json             # Configuración del firewall
├── myTopo.py             # Topología de red
├── run_pox.sh            # Script para iniciar POX
└── run_mininet.sh        # Script para iniciar Mininet
```

# Ejecución del programa

Estando ubicado en la raíz del proyecto:

#### Terminal 1 - Iniciar POX:
```bash
./run_pox.sh
```

#### Terminal 2 - Iniciar Mininet:
```bash
./run_mininet.sh n
```
Donde n sera la cantidad de switches que tendrá la red, por defecto serán dos

### Para detener:

- **POX**: `Ctrl+C` en la terminal del controlador
- **Mininet**: Escribir `exit` en el prompt de Mininet

# Configuración del Firewall

### Archivo `rules.json`

Define qué switch actuará como firewall y las reglas a aplicar:

```json
{
  "switch_with_firewall": 1,
  "firewall_rules": [
    {
      "rule_id": 1,
      "description": "Bloquear puerto 80",
      "match": {
        "tp_dst": 80
      }
    }
  ]
}
```

# Topología de la red construida

```
    h1 ──┐                  ┌── h3
         │                  │
        s1 ────── s2 ────── sn
         │                  │
    h2 ──┘                  └── h4

Leyenda:
  h1, h2, h3, h4 = Hosts
  s1, s2, s3, ..., sn = Switches OpenFlow
```

### Distribución de Hosts:
- **s1** (Switch 1): h1 (10.0.0.1), h2 (10.0.0.2)
- **s2** (Switch 2): Switch intermedio
- **s3** (Switch 3): h3 (10.0.0.3), h4 (10.0.0.4)

# Reglas del Firewall

### Regla 1: Bloqueo de Puerto 80
- **Descripción**: Bloquear todo el tráfico TCP con puerto destino 80
- **Match**: `tp_dst: 80`
- **Protocolo**: TCP (asumido por defecto)
- **Acción**: DROP

### Regla 2: Bloqueo UDP desde h1 al Puerto 5001
- **Descripción**: Bloquear tráfico UDP desde 10.0.0.1 al puerto 5001
- **Match**: `nw_src: 10.0.0.1, nw_proto: 17, tp_dst: 5001`
- **Protocolo**: UDP (17)
- **Acción**: DROP

### Regla 3: Bloqueo Bidireccional h2 ↔ h3
- **Descripción**: Bloquear toda comunicación entre 10.0.0.2 y 10.0.0.3
- **Match**: Dos reglas bidireccionales
  - `nw_src: 10.0.0.2, nw_dst: 10.0.0.3`
  - `nw_src: 10.0.0.3, nw_dst: 10.0.0.2`
- **Acción**: DROP

# Pruebas

## En Mininet:

```bash
# Ver conectividad general
mininet> pingall

# Abrir terminales de hosts
mininet> xterm h1 h2 h3 h4

# Ver flujos instalados en un switch
mininet> dpctl dump-flows tcp:127.0.0.1:6634
```

### Probar funcionamiento de regla 1
```bash
mininet> h3 iperf -s -p 80 &
mininet> xterm h1
xterm> sudo wireshark -k -i h1-eth0
mininet> h1 iperf -c 10.0.0.3 -p 80
```

Se podrá observar en la captura que los paquetes TCP SYN que envía h1 nunca son respondidos por h3, ya que son dropeados antes

### Probar funcionamiento de regla 2 (desde h1)
```bash
mininet> h3 iperf -s -u -p 5001 &
mininet> xterm h1
xterm> sudo wireshark -k -i h1-eth0
mininet> h1 iperf -u -c 10.0.0.3 -p 5001 -t 2
```

Se podrá observar en la captura que los paquetes UDP que envía h1 nunca son respondidos por h3, ya que son dropeados antes

### Probar funcionamiento de regla 3 (desde h2 y h3)

1) En el sentido h2 → h3

```bash
mininet> h3 iperf -s -p 5001 &
mininet> xterm h2
xterm> sudo wireshark -k -i h2-eth0
mininet> h2 iperf -c 10.0.0.3 -p 5001 -t 2
```

Se podrá observar en la captura que los paquetes TCP SYN que envía h2 nunca son respondidos por h3, ya que son dropeados antes

2) En el sentido h3 → h2

```bash
mininet> h2 iperf -s -p 5001 &
mininet> xterm h3
xterm> sudo wireshark -k -i h3-eth0
mininet> h3 iperf -c 10.0.0.2 -p 5001 -t 2
```

Se podrá observar en la captura que los paquetes TCP SYN que envía h3 nunca son respondidos por h2, ya que son dropeados antes


## Pruebas automatizadas

### Pingall
Levanta la topología, ejecuta `pingall` y termina Mininet.

```bash
# Terminal 1:
./run_pox.sh

# Terminal 2:
sudo ./test_pingall.sh [num_switches]
```

- `num_switches` es opcional (por defecto 2).
- Resultado esperado con las reglas actuales: solo se bloquea h2↔h3 (regla 3); el resto responde.
- Mininet se cierra solo al terminar la prueba.

### Bloqueo de puerto 80 con iperf
Verifica la regla 1 (descartar tráfico con puerto destino 80).

```bash
# Terminal 1:
./run_pox.sh

# Terminal 2:
sudo ./test_block_port80.sh [num_switches]
```

- `num_switches` es opcional (por defecto 2).
- La prueba lanza un servidor iperf en h3 (puerto 80) y un cliente desde h1 al puerto 80 de h3. Se muestra el exit code de iperf y el tail del log, en ~1–3 segundos.
- Resultado esperado: `OK: puerto 80 bloqueado` y `iperf_exit` distinto de 0. Si aparece `FAIL`, el tráfico no se bloqueó o iperf no pudo conectarse.
- Mininet se cierra al finalizar la prueba.
- Opcional: `WAIT_BEFORE=5` (por defecto 5) para esperar unos segundos antes de generar tráfico

### Bloqueo UDP puerto 5001 desde h1 con iperf
Verifica la regla 2 (descartar tráfico UDP desde h1 con puerto destino 5001).

```bash
# Terminal 1:
./run_pox.sh

# Terminal 2:
sudo ./test_block_udp5001.sh [num_switches]
```

- `num_switches` es opcional (por defecto 2).
- h3 corre `iperf -s -u -p 5001`; h1 corre `iperf -c 10.0.0.3 -u -p 5001`. Se muestra el exit code del cliente y el tail del log.
- Resultado esperado: `OK: UDP 5001 bloqueado (no se registró tráfico)` en el servidor. Si aparece `FAIL`, el tráfico pasó.
- Mininet se cierra al finalizar la prueba.
- Opcional: `WAIT_BEFORE=5` (por defecto 5) para esperar unos segundos antes de generar tráfico

### Bloqueo h2 ↔ h3 con iperf
Verifica la regla 3 (bloqueo bidireccional entre 10.0.0.2 y 10.0.0.3).

```bash
# Terminal 1:
./run_pox.sh

# Terminal 2:
sudo ./test_block_hosts23.sh [num_switches]
```

- `num_switches` es opcional (por defecto 2).
- Prueba en ambos sentidos con iperf TCP puerto 5001: h2→h3 y h3→h2. Se muestran los exit codes y el tail de cada log.
- Resultado esperado: `OK: h2 -> h3 bloqueado` y `OK: h3 -> h2 bloqueado`. Si aparece `FAIL`, el bloqueo no se aplicó.
- Mininet se cierra al finalizar la prueba.
- Opcional: `WAIT_BEFORE=5` (por defecto 5) para esperar unos segundos antes de generar tráfico



## Error compatibilidad POX - Python3 (solo seguir las instrucciones en caso de error):

Buscamos el directorio:
```bash
cd ~/pox
```

BackUp del archivo original:
```bash
cp "$POX_DIR/pox/lib/packet/dns.py" "$POX_DIR/pox/lib/packet/dns.py.bak"
```

Copiar el dns.py de tu proyecto al POX
```bash
cp /ruta/a/tu/proyecto/dns.py "$POX_DIR/pox/lib/packet/dns.py"
```

Ajustar permisos
```bash
chmod 644 "$POX_DIR/pox/lib/packet/dns.py"
ls -l "$POX_DIR/pox/lib/packet/dns.py" "$POX_DIR/pox/lib/packet/dns.py.bak"
```

Detener e iniciar nuevamente
```bash
pkill -f pox.py || true
cd "$POX_DIR"
python3 ./pox.py log.level --DEBUG misc.firewall
```

Restaurar al backup (solo caso de error)
```bash
mv "$POX_DIR/pox/lib/packet/dns.py.bak" "$POX_DIR/pox/lib/packet/dns.py"
```