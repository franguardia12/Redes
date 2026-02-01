#!/bin/bash

# Prueba: bloqueo bidireccional entre h2 (10.0.0.2) y h3 (10.0.0.3) según regla 3.
# Usa iperf en TCP (puerto 5001) en ambos sentidos.

if [ "$EUID" -ne 0 ]; then
  echo "Este script requiere privilegios de root. Ejecuta con: sudo $0 [num_switches]"
  exit 1
fi

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NUM_SWITCHES="${1:-2}"
WAIT_BEFORE="${WAIT_BEFORE:-5}"

echo "============================================"
echo "  Test: bloqueo h2 <-> h3 (regla 3)"
echo "============================================"
echo "Topología: mytopo,$NUM_SWITCHES (archivo: $SCRIPT_DIR/myTopo.py)"
echo "Controlador: remote (127.0.0.1:6633)"
echo "Pruebas: h2->h3 y h3->h2 con iperf TCP puerto 5001 (espera bloqueo en ambos sentidos)"
echo "Esperando $WAIT_BEFORE segundos..."
sleep "$WAIT_BEFORE"
echo ""

echo "Limpiando estado previo de Mininet..."
mn -c >/dev/null 2>&1 || true

mn --custom "$SCRIPT_DIR/myTopo.py" \
   --topo "mytopo,$NUM_SWITCHES" \
   --controller=remote,ip=127.0.0.1,port=6633 <<'EOF'
# --- h2 -> h3 ---
h3 iperf -s -p 5001 > /tmp/iperf-h3-server.log 2>&1 &
h3 sleep 1
h3 pgrep iperf >/dev/null || { echo "ERROR: no se pudo iniciar iperf en h3"; exit; }
h2 bash -c "timeout 5s iperf -c 10.0.0.3 -p 5001 -t 1 -i 0.5 > /tmp/iperf-h2-client.log 2>&1; RC=$?; echo \"h2->h3_exit=${RC:-unset}\"; tail -n 5 /tmp/iperf-h2-client.log; if [ \"${RC:-1}\" -eq 0 ]; then echo 'FAIL: h2 -> h3 no fue bloqueado'; else echo 'OK: h2 -> h3 bloqueado'; fi"
h3 pkill iperf || true

# --- h3 -> h2 ---
h2 iperf -s -p 5001 > /tmp/iperf-h2-server.log 2>&1 &
h2 sleep 1
h2 pgrep iperf >/dev/null || { echo "ERROR: no se pudo iniciar iperf en h2"; exit; }
h3 bash -c "timeout 5s iperf -c 10.0.0.2 -p 5001 -t 1 -i 0.5 > /tmp/iperf-h3-client.log 2>&1; RC=$?; echo \"h3->h2_exit=${RC:-unset}\"; tail -n 5 /tmp/iperf-h3-client.log; if [ \"${RC:-1}\" -eq 0 ]; then echo 'FAIL: h3 -> h2 no fue bloqueado'; else echo 'OK: h3 -> h2 bloqueado'; fi"
h2 pkill iperf || true
exit
EOF
