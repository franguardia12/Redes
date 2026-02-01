#!/bin/bash

# Prueba: verifica que el firewall bloquee tráfico TCP al puerto 80.
# Levanta Mininet con la topología y ejecuta iperf (h3 servidor, h1 cliente).

if [ "$EUID" -ne 0 ]; then
  echo "Este script requiere privilegios de root. Ejecuta con: sudo $0 [num_switches]"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NUM_SWITCHES="${1:-2}"
WAIT_BEFORE="${WAIT_BEFORE:-5}"

echo "============================================"
echo "  Test: bloqueo de puerto 80 con iperf"
echo "============================================"
echo "Topología: mytopo,$NUM_SWITCHES (archivo: $SCRIPT_DIR/myTopo.py)"
echo "Controlador: remote (127.0.0.1:6633)"
echo "Prueba: h3 iperf -s -p 80 ; h1 iperf -c 10.0.0.3 -p 80 (espera bloqueo)"
echo "Esperando $WAIT_BEFORE segundos..."
sleep "$WAIT_BEFORE"
echo ""

echo "Limpiando estado previo de Mininet..."
mn -c >/dev/null 2>&1 || true

mn --custom "$SCRIPT_DIR/myTopo.py" \
   --topo "mytopo,$NUM_SWITCHES" \
   --controller=remote,ip=127.0.0.1,port=6633 <<'EOF'
# Levantar servidor iperf en h3 puerto 80
h3 iperf -s -p 80 > /tmp/iperf80-server.log 2>&1 &
h3 sleep 1
h3 pgrep iperf >/dev/null || { echo "ERROR: no se pudo iniciar iperf en h3"; exit; }
# Ejecutar cliente desde h1 hacia h3 puerto 80 (se espera que falle si la regla bloquea)
h1 bash -c "iperf -c 10.0.0.3 -p 80 -t 1 -i 0.5 > /tmp/iperf80-client.log 2>&1; RC=$?; echo \"iperf_exit=${RC:-unset}\"; tail -n 5 /tmp/iperf80-client.log; if [ \"${RC:-1}\" -eq 0 ]; then echo 'FAIL: puerto 80 no fue bloqueado'; else echo 'OK: puerto 80 bloqueado'; fi"
# Detener iperf en h3
h3 pkill iperf || true
exit
EOF
