#!/bin/bash

# Script para ejecutar POX desde el proyecto
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Permite usar una instalación externa de POX exportando POX_HOME
POX_HOME="${POX_HOME:-"$SCRIPT_DIR/pox"}"

# Fallback a ~/pox si existe y no se encontró en el proyecto
if [ ! -f "$POX_HOME/pox.py" ] && [ -f "$HOME/pox/pox.py" ]; then
  POX_HOME="$HOME/pox"
fi

# Ruta a las reglas (se puede sobrescribir con RULES_FILE en el entorno)
RULES_FILE="${RULES_FILE:-"$SCRIPT_DIR/rules.json"}"

if [ ! -f "$POX_HOME/pox.py" ]; then
  echo "No se encontró pox.py en $POX_HOME"
  echo "Clona POX en $SCRIPT_DIR/pox o exporta POX_HOME apuntando a tu instalación."
  exit 1
fi

cd "$POX_HOME"

echo "============================================"
echo "  Iniciando POX Firewall"
echo "============================================"
echo ""
echo "Proyecto: $SCRIPT_DIR"
echo "Reglas: $RULES_FILE"
echo "POX_HOME: $POX_HOME"
echo ""
echo "Presiona Ctrl+C para detener"
echo ""

# Exporta RULES_FILE para que el módulo firewall lo lea
RULES_FILE="$RULES_FILE" ./pox.py log.level --DEBUG firewall
