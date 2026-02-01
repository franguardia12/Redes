import queue as q
from lib.datagram import Datagram
import re
import os
from lib.common import (
    log,
    CHUNK_SIZE,
    MSS,
    H_SIZE,
    MAX_WAIT_PACKETS,
    MAX_WINDOWS_RETRIES,
)
import logging

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


class SW:
    def __init__(self, sock, server_address, destination, filename, vrb):
        self.socket = sock
        self.srv_adr = server_address
        self.destination = destination
        self.filename = filename
        self.queue = None
        self.vrb = vrb

    def setFilename(self, filename):
        self.filename = filename

    def send(self, queue):
        self.queue = queue
        window_retries_continue = 0
        log("Enviando archivo con S&W", logging.INFO, self.vrb)
        file = f"{self.destination}/{self.filename}"
        log(f"Archivo a enviar: {file}", logging.INFO, self.vrb)
        filesize = os.path.getsize(file)
        with open(file, "rb") as f:
            seq = 0
            total_c = (filesize // CHUNK_SIZE) + 1
            log(f"Total chunks to send: {total_c}", logging.INFO, self.vrb)
            for i in range(total_c):
                window_retries_continue = 0
                log(
                    f"Enviando chunk {i} de {total_c}",
                    logging.INFO,
                    self.vrb,
                )

                chunk = f.read(CHUNK_SIZE)
                is_last = 1 if i == total_c - 1 else 0
                packet = f"{seq}:{is_last}:".encode() + chunk

                ack_received = False
                while not ack_received:
                    log(
                        f"[→] Enviando fragmento {seq}",
                        logging.INFO,
                        self.vrb,
                    )
                    self.socket.sendto(packet, (self.srv_adr))

                    try:
                        data = self.queue.get(timeout=2)
                        ack = self._extract_ack(data)
                        log(f"[←] Paquete rec: {ack}", logging.INFO, self.vrb)
                        if ack == f"ACK{seq}":
                            log(f"[✓] Recibido {ack}", logging.INFO, self.vrb)
                            ack_received = True
                            window_retries_continue = 0
                            seq = 1 - seq
                        else:
                            log(
                                "[!] ACK incorrecto, retransmitiendo...",
                                logging.WARNING,
                                self.vrb,
                            )
                    except q.Empty:
                        log(
                            "[!] Timeout, retransmitiendo...",
                            logging.WARNING,
                            self.vrb,
                        )
                        window_retries_continue += 1
                        if window_retries_continue >= MAX_WINDOWS_RETRIES:
                            log(
                                "[!] Máximo de reenvio.",
                                logging.ERROR,
                                self.vrb,
                            )
                            return False

        log("Archivo enviado correctamente.", logging.INFO, self.vrb)

    def sendAction(self, datagram: Datagram):
        ackReceived = False
        seq = 1
        while ackReceived is False:
            log(f"server address: {self.srv_adr}", logging.INFO, self.vrb)
            self.socket.sendto(datagram.to_bytes(), (self.srv_adr))
            try:
                modifiedMessage, _ = self.socket.recvfrom(MSS + H_SIZE)
                log(
                    f"Data received size: {len(modifiedMessage)}",
                    logging.INFO,
                    self.vrb,
                )
                datagram = Datagram.from_bytes(modifiedMessage)
                modifiedMessage = datagram.data
                if modifiedMessage.decode() == f"ACK{seq}":
                    log(
                        f"ACK recibido: {modifiedMessage.decode()}",
                        logging.INFO,
                        self.vrb,
                    )
                    ackReceived = True
                else:
                    log("Renviando mensaje", logging.INFO, self.vrb)
                    continue
            except TimeoutError:
                log(
                    "Timeout alcanzado, reenviando mensaje",
                    logging.INFO,
                    self.vrb,
                )
                continue

    def str(self):
        return "SW"

    def receive(self, queue):
        self.queue = queue
        exp_s = 0
        endConection = 0
        destination_file = f"{self.destination}/{self.filename}"
        finish = False
        with open(destination_file, "wb") as f:
            while True:
                try:
                    data = self.queue.get(timeout=2)
                    log(
                        f"[←] Paquete recibido, tamaño={len(data)} bytes",
                        logging.INFO,
                        self.vrb,
                    )
                    endConection = 0

                    parts = data.split(b":", 2)
                    seq = int(parts[0].decode())
                    is_last = int(parts[1].decode())
                    chunk = parts[2]

                    if seq == exp_s:
                        f.write(chunk)
                        self.socket.sendto(f"ACK{seq}".encode(), self.srv_adr)
                        log(
                            f"[✓] Fragmento {seq} recibido, enviado ACK{seq}",
                            logging.INFO,
                            self.vrb,
                        )
                        exp_s = 1 - exp_s
                        if is_last == 1:
                            finish = True
                    else:
                        if not finish:
                            msg_ack = f"ACK{1-exp_s}".encode()
                            self.socket.sendto(msg_ack, self.srv_adr)
                            log(
                                f"[!] Duplicado {seq}, reenviado ACK{1-exp_s}",
                                logging.WARNING,
                                self.vrb,
                            )
                        else:
                            break
                except q.Empty:
                    if finish:
                        log(
                            "Recepción finalizada tras último paquete.",
                            logging.INFO,
                            self.vrb,
                        )
                        break
                    else:
                        log("Esperando paquetes", logging.DEBUG, self.vrb)
                        endConection += 1
                        if endConection >= MAX_WAIT_PACKETS:
                            log(
                                "No se recibieron más paquetes, finalizando.",
                                logging.INFO,
                                self.vrb,
                            )
                            return False

        log("Archivo descargado correctamente.", logging.INFO, self.vrb)
        return True

    def _extract_ack(self, raw_data: bytes) -> str:
        if not raw_data:
            return ""

        def _match_ack(text: str) -> str | None:
            match = re.search(r"ACK\d+", text)
            if match:
                return match.group(0)
            return None

        try:
            datagram = Datagram.from_bytes(raw_data)
            payload = datagram.data.decode(errors="ignore")
            header = datagram.header.decode(errors="ignore")
            for fragment in (payload, header):
                ack = _match_ack(fragment)
                if ack:
                    return ack
        except Exception:
            pass

        decoded = raw_data.decode(errors="ignore")
        ack = _match_ack(decoded)
        if ack:
            return ack
        return decoded.replace("\0", "").strip()
