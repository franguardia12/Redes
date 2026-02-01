#!/bin/bash

# Prueba: bloquea tráfico UDP desde h1 al puerto 5001 (regla 2).
# Usa iperf en modo UDP: h3 como servidor, h1 como cliente.

if [ "$EUID" -ne 0 ]; then
  echo "Este script requiere privilegios de root. Ejecuta con: sudo $0 [num_switches]"
  exit 1
fi

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NUM_SWITCHES="${1:-2}"
WAIT_BEFORE="${WAIT_BEFORE:-5}"

echo "============================================"
echo "  Test: bloqueo UDP 5001 desde h1"
echo "============================================"
echo "Topología: mytopo,$NUM_SWITCHES (archivo: $SCRIPT_DIR/myTopo.py)"
echo "Controlador: remote (127.0.0.1:6633)"
echo "Prueba: h3 iperf -s -u -p 5001 ; h1 iperf -c 10.0.0.3 -u -p 5001 (espera bloqueo)"
echo "Esperando $WAIT_BEFORE segundos..."
sleep "$WAIT_BEFORE"
echo ""

echo "Limpiando estado previo de Mininet..."
mn -c >/dev/null 2>&1 || true

mn --custom "$SCRIPT_DIR/myTopo.py" \
   --topo "mytopo,$NUM_SWITCHES" \
   --controller=remote,ip=127.0.0.1,port=6633 <<'EOF'
# Iniciar servidor iperf UDP en h3 puerto 5001
h3 iperf -s -u -p 5001 -i 1 > /tmp/iperf5001-server.log 2>&1 &
h3 sleep 1
h3 pgrep iperf >/dev/null || { echo "ERROR: no se pudo iniciar iperf en h3"; exit; }

# Cliente UDP desde h1 hacia h3:5001 (se espera bloqueo)
h1 bash -c "iperf -c 10.0.0.3 -u -p 5001 -b 5M -t 2 -i 1 > /tmp/iperf5001-client.log 2>&1; RC=\$?; echo \"client_exit=\${RC:-unset}\"; tail -n 5 /tmp/iperf5001-client.log"

# Esperar un instante y evaluar si el servidor recibió datos
h3 sleep 1
h3 bash -c "if grep -q 'MBytes' /tmp/iperf5001-server.log; then echo 'FAIL: UDP 5001 NO bloqueado (se recibieron datos)'; else echo 'OK: UDP 5001 bloqueado (no se registró tráfico)'; fi"

# Detener iperf en h3
h3 pkill iperf || true
exit
EOF
