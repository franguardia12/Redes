#!/bin/bash

# Prueba automatizada: levanta Mininet con la topología custom y ejecuta pingall.

if [ "$EUID" -ne 0 ]; then
  echo "Este script requiere privilegios de root. Ejecuta con: sudo $0 [num_switches]"
  exit 1
fi

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NUM_SWITCHES="${1:-2}"

echo "============================================"
echo "  Test: pingall sobre myTopo"
echo "============================================"
echo "Topología: mytopo,$NUM_SWITCHES (archivo: $SCRIPT_DIR/myTopo.py)"
echo "Controlador: remote (127.0.0.1:6633)"
echo "Prueba: pingall (Mininet se cerrará solo al terminar la prueba)"
echo ""

echo "Limpiando estado previo de Mininet..."
mn -c >/dev/null 2>&1 || true

mn --custom "$SCRIPT_DIR/myTopo.py" \
   --topo "mytopo,$NUM_SWITCHES" \
   --controller=remote,ip=127.0.0.1,port=6633 \
   --test pingall
