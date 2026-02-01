from queue import Queue
from threading import Thread
from lib.datagram import Datagram
from lib.common import Action
from lib.common import log, MSS, H_SIZE, TIMEOUT_COEFFICIENT, INITIAL_RTT
import logging
import sys
import select

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
CLIENT_MAX_RETRIES = 5


class Client:
    def __init__(self, sckt, s_adr, recovery, storage, filename, vrb):
        self.server_address = s_adr
        self.recovery = recovery
        self.storage = storage
        self.socket = sckt
        self.socket.settimeout(INITIAL_RTT * TIMEOUT_COEFFICIENT)
        self.queue = Queue()
        self.filename = filename
        self.vrb = vrb

    def start(self, action: Action):

        self.connection(action)
        thread = None
        if action == Action.UPLOAD:
            log(f"Upload para {self.filename}", logging.INFO, self.vrb)
            thread = Thread(target=self._safe_send, args=(self.queue,))
        elif action == Action.DOWNLOAD:
            thread = Thread(target=self._safe_receive, args=(self.queue,))

        if thread:
            thread.start()
            try:
                while thread.is_alive():
                    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                        user_input = sys.stdin.readline().strip()
                        if user_input.lower() == "q":
                            log(
                                "Se presionó 'q'. Cerrando cliente...",
                                logging.INFO,
                                self.vrb,
                            )
                            self.socket.close()
                            return

                    try:
                        data, _ = self.socket.recvfrom(MSS + H_SIZE)
                        if data == b"FINISHED":
                            log(
                                "Transferencia finalizada, cerrando cliente.",
                                logging.INFO,
                                self.vrb,
                            )
                            break
                        if action == Action.UPLOAD:
                            log(
                                f"Mensaje recibido: {data.decode()}",
                                logging.DEBUG,
                                self.vrb,
                            )
                        self.queue.put(data)
                    except TimeoutError:
                        continue
                if action == Action.UPLOAD:
                    log(
                        f"Carga terminada para {self.filename}",
                        logging.INFO,
                        self.vrb,
                    )
                    self.socket.close()
                elif action == Action.DOWNLOAD:
                    log(
                        f"Descarga terminada para {self.filename}",
                        logging.INFO,
                        self.vrb,
                    )
                    self.socket.close()
            except KeyboardInterrupt:
                log("Apagando cliente...", logging.INFO, self.vrb)
            finally:
                self.socket.close()

    def _safe_send(self, queue):
        try:
            self.recovery.send(queue)
        except (OSError, Exception) as e:
            log(f"Error en envío: {e}", logging.INFO, self.vrb)

    def _safe_receive(self, queue):
        try:
            self.recovery.receive(queue)
        except (OSError, Exception) as e:
            log(f"Error en recepción: {e}", logging.INFO, self.vrb)

    def connection(self, action: Action):
        seq = 0
        message = self._build_init_message(action)
        ackReceived = False
        header = self._build_header()
        datagram = Datagram(header=header, data=message.encode())
        connection_retries = 0

        while not ackReceived:
            self._send_init_packet(datagram)
            connection_retries += 1
            if connection_retries > CLIENT_MAX_RETRIES:
                log(
                    "No se pudo establecer conexión con el servidor",
                    logging.ERROR,
                    self.vrb,
                )
                self.socket.close()
                exit(1)
            try:
                ackReceived = self._wait_for_ack(seq)
            except TimeoutError:
                log(
                    "Timeout alcanzado, reenviando mensaje",
                    logging.INFO,
                    self.vrb,
                )
                continue
            except Exception as e:
                log(f"Error: {e}", logging.ERROR, self.vrb)
                self.socket.close()
                exit(1)
        log("Cliente aceptado por el servidor", logging.INFO, self.vrb)

    def _build_init_message(self, action: Action):
        log(
            "Enviando al servidor que protocolo quiero utilizar",
            logging.INFO,
            self.vrb,
        )
        message = self.recovery.str() + f" {action.name} {self.filename}"
        log(f"Mensaje a enviar: {message}", logging.INFO, self.vrb)
        return message

    def _build_header(self):
        return "INIT".ljust(H_SIZE, "\0").encode()

    def _send_init_packet(self, datagram):
        log("Enviando paquete...", logging.DEBUG, self.vrb)
        self.socket.sendto(datagram.to_bytes(), (self.server_address))
        log("Esperando respuesta del servidor...", logging.DEBUG, self.vrb)

    def _wait_for_ack(self, seq):
        modifiedMessage, _ = self.socket.recvfrom(MSS + H_SIZE)
        log("Mensaje recibido del servidor", logging.DEBUG, self.vrb)
        datagram = Datagram.from_bytes(modifiedMessage)
        modifiedMessage = datagram.data
        msg_decoded = modifiedMessage.decode()

        if msg_decoded.startswith("ERROR"):
            error_msg = msg_decoded.replace("ERROR", "").strip()
            log(f"Error del servidor: {error_msg}", logging.ERROR, self.vrb)
            raise Exception(f"Error del servidor: {error_msg}")
        if msg_decoded == f"ACK{seq}":
            log(f"Mensaje recibido: {msg_decoded}", logging.DEBUG, self.vrb)
            return True
        else:
            log("Renviando mensaje", logging.INFO, self.vrb)
            return False
