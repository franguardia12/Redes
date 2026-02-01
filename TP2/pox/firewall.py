from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import EventMixin
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr
from pox.lib.packet import ipv4
import os
import json

log = core.getLogger()

# Permite sobrescribir la ubicación de rules.json mediante la variable de entorno RULES_FILE.
# Por defecto busca el archivo en la raíz del proyecto (un nivel por encima de este archivo).
RULES_FILE = os.environ.get(
	"RULES_FILE",
	os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "rules.json")),
)
class Firewall(EventMixin):
	def __init__(self):
		self.listenTo(core.openflow)
		log.debug("Enabling Firewall Module")
		self.rules, self.switch_assigned = self._load_rules()
		self.rules_installed = set()  # Rastrear switches con reglas instaladas

	def _load_rules(self):
		try:
			with open(RULES_FILE, 'r') as f:
				data = json.load(f)
				switch_assigned = data.get('switch_with_firewall')
				rules = data.get('firewall_rules', [])
				log.info("Loaded %d firewall rules from %s", len(rules), RULES_FILE)
    
				return rules, switch_assigned
		except Exception as e:
			log.error("Error loading rules from %s: %s", RULES_FILE, str(e))
			return [], None

	def _check_firewall_rules(self, connection, dpid):
		dpid_numeric = dpid.split('-')[-1]  # Obtener la parte numérica del DPID
		print("DPID received in _check_firewall_rules is:", dpid_numeric)
		switch_id = int(dpid_numeric, 16)
		
		# Verificar si ya instalamos las reglas en este switch
		if dpid in self.rules_installed:
			log.info("Rules already installed on switch %s. Skipping.", dpid)
			return
		
		# Si es el switch asignado para el firewall, instalar reglas específicas
		if switch_id == self.switch_assigned:
			log.info("Installing firewall rules on assigned switch %s", dpid)
			for rule in self.rules:
				rule_id = rule.get('rule_id')
				description = rule.get('description')
				action = rule.get('action')
				match_criteria = rule.get('match')
				
				
				if isinstance(match_criteria, list):
					for match_item in match_criteria:
						self._add_flow_rule(connection, match_item, action, rule_id)
				else:
					self._add_flow_rule(connection, match_criteria, action, rule_id)
		else:
			log.info("Switch %s is not the firewall switch. Installing default allow rule only.", dpid)
		
		# Instalar regla por defecto en TODOS los switches (permitir tráfico normal)
		msg = of.ofp_flow_mod()
		msg.priority = 1 
		msg.actions.append(of.ofp_action_output(port=of.OFPP_NORMAL))
		connection.send(msg)
		
		# Marcar que las reglas fueron instaladas en este switch
		self.rules_installed.add(dpid)
		log.info("Rules successfully installed on switch %s", dpid)

	def _add_flow_rule(self, connection, match_dict, action, rule_id):
		msg = of.ofp_flow_mod()
		match = of.ofp_match()

		# Normaliza claves del JSON a los nombres que espera POX
		normalized = dict(match_dict) if match_dict else {}
		if "src_ip" in normalized:
			normalized["nw_src"] = normalized.pop("src_ip")
		if "dst_ip" in normalized:
			normalized["nw_dst"] = normalized.pop("dst_ip")
		if "src_port" in normalized:
			normalized["tp_src"] = normalized.pop("src_port")
		if "dst_port" in normalized:
			normalized["tp_dst"] = normalized.pop("dst_port")
		if "protocol" in normalized:
			proto = normalized.pop("protocol")
			if isinstance(proto, str):
				proto_map = {"TCP": 6, "UDP": 17}
				normalized["nw_proto"] = proto_map.get(proto.upper(), proto)
			else:
				normalized["nw_proto"] = proto

		#Chequear si se usa el puerto 80
		if any(key in normalized for key in ['nw_src', 'nw_dst', 'nw_proto', 'tp_dst', 'tp_src']):
			match.dl_type = 0x0800 
		
		#Chequeo las reglas dos y tres
		if 'nw_src' in normalized:
			match.nw_src = IPAddr(normalized['nw_src'])
		if 'nw_dst' in normalized:
			match.nw_dst = IPAddr(normalized['nw_dst'])
		if 'nw_proto' in normalized:
			match.nw_proto = normalized['nw_proto']
   
		#ASUMO que si hay tp_dst o tp_src y no esta aclarado el protocolo es TCP
		if 'tp_dst' in normalized:
			match.tp_dst = normalized['tp_dst']
			if 'nw_proto' not in normalized:
				match.nw_proto = 6  # TCP
		if 'tp_src' in normalized:
			match.tp_src = normalized['tp_src']
			if 'nw_proto' not in normalized:
				match.nw_proto = 6  # TCP
		
		msg.match = match
		msg.priority = 10 + rule_id  # Prioridad basada en rule_id
		
		if action == "drop":
			log.debug("Installing drop rule: %s", match_dict)
			pass
		elif action == "forward":
			log.debug("Installing forward rule: %s", match_dict)
			msg.actions.append(of.ofp_action_output(port=of.OFPP_NORMAL))
		
		connection.send(msg)
		log.debug("Flow rule installed with match: %s, action: %s", match_dict, action)

	def _handle_ConnectionUp(self, event):
		"""
		Evento de conexión: instala reglas según configuración.
		"""
		self._check_firewall_rules(event.connection, dpidToStr(event.dpid))

def launch():
	core.registerNew(Firewall)
