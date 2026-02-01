#!/bin/bash

# Script para iniciar Mininet con la topología personalizada

cd "$(dirname "$0")"

# Número de switches (por defecto 2)
NUM_SWITCHES=${1:-2}

echo "============================================"
echo "  Iniciando Mininet"
echo "============================================"
echo ""
echo "Topología: myTopo.py"
echo "Número de switches: $NUM_SWITCHES"
echo "Controlador: remote (127.0.0.1:6633)"
echo ""
echo "Comandos útiles en mininet:"
echo "  - pingall: probar conectividad"
echo "  - xterm h1 h2: abrir terminales"
echo "  - exit: salir"
echo ""

sudo mn --custom myTopo.py --topo mytopo,$NUM_SWITCHES --controller=remote,ip=127.0.0.1,port=6633
