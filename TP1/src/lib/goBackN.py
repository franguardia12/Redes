import time
import queue as q
from lib.datagram import Datagram
from lib.common import (
    H_SIZE,
    log,
    MSS,
    TIMEOUT_COEFFICIENT,
    WINDOW_SIZE,
    GBN_MIN_TIMEO,
    GBN_ALPHA,
    GBN_BETA,
    INITIAL_RTT,
    MAX_WAIT_PACKETS,
    END_MAX_RETRIES,
    MAX_WINDOWS_RETRIES,
)
import logging

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

P = "Paquete"


class GBN:
    def __init__(self, socket, srv_adr, destination, filename, verbosity):
        self.socket = socket
        self.srv_addr = srv_adr
        self.destination = destination
        self.filename = filename
        self.queue = None
        self.vrb = verbosity
        self.est_rtt = INITIAL_RTT
        self.dev_rtt = INITIAL_RTT / 2
        self.timeout = max(GBN_MIN_TIMEO, INITIAL_RTT)

    def setFilename(self, filename):
        self.filename = filename

    def str(self):
        return "GBN"

    def send(self, queue):
        self.queue = queue
        log("Subiendo archivo con Go-Back-N", logging.INFO, self.vrb)

        base = 0
        next_seq = 0
        window_retries_continue = 0
        window = []

        file_path = f"{self.destination}/{self.filename}"
        chunks = []

        try:
            with open(file_path, "rb") as f:
                while True:
                    data = f.read(MSS)
                    if not data:
                        break
                    chunks.append(data)

            t = len(chunks)
            log(f"Archivo dividido en {t} paquetes", logging.DEBUG, self.vrb)

            while base < t:
                while next_seq < base + WINDOW_SIZE and next_seq < t:
                    is_last = 1 if next_seq == t - 1 else 0
                    h = f"DATA{next_seq}:{is_last}".ljust(H_SIZE, "\0")
                    packet = Datagram(h.encode(), chunks[next_seq]).to_bytes()
                    s_time = time.monotonic()
                    self.socket.sendto(packet, self.srv_addr)
                    log(
                        f"[→] Enviado paquete {next_seq} (is_last={is_last})",
                        logging.DEBUG,
                        self.vrb,
                    )
                    window.append(
                        {"seq": next_seq, "packet": packet, "sent_at": s_time}
                    )
                    next_seq += 1

                try:
                    if window:
                        elapsed = time.monotonic() - window[0]["sent_at"]
                        wait = max(self.timeout - elapsed, GBN_MIN_TIMEO)
                    else:
                        wait = self.timeout
                    raw_ack = self.queue.get(timeout=wait)

                    ack_datagram = Datagram.from_bytes(raw_ack)
                    ack_header = ack_datagram.header.decode().strip("\0")

                    if ack_header.startswith("ACK"):
                        ack_num = int(ack_header.replace("ACK", ""))
                    log(f"[✓] Recibido {ack_header}", logging.INFO, self.vrb)

                    if ack_num >= base:
                        shift = (ack_num + 1) - base
                        if window:
                            sample_rt = time.monotonic() - window[0]["sent_at"]
                            self.est_rtt = (
                                1 - GBN_ALPHA
                            ) * self.est_rtt + GBN_ALPHA * sample_rt
                            self.dev_rtt = (
                                1 - GBN_BETA
                            ) * self.dev_rtt + GBN_BETA * abs(
                                sample_rt - self.est_rtt
                            )
                            self.timeout = max(
                                GBN_MIN_TIMEO, self.est_rtt + 4 * self.dev_rtt
                            )

                        base = ack_num + 1
                        window = window[shift:]

                except q.Empty:
                    log(
                        "[!] Timeout: reenviando ventana",
                        logging.WARNING,
                        self.vrb,
                    )
                    window_retries_continue += 1
                    if window_retries_continue >= MAX_WINDOWS_RETRIES:
                        log(
                            "[!] Max de reintentos consecutivos de ventana.",
                            logging.ERROR,
                            self.vrb,
                        )
                        return False
                    for i, entry in enumerate(window):
                        seq = base + i
                        self.socket.sendto(entry["packet"], self.srv_addr)
                        entry["sent_at"] = time.monotonic()
                        log(
                            f"[↻] Reenviado paquete {seq}",
                            logging.DEBUG,
                            self.vrb,
                        )
                else:
                    window_retries_continue = 0

            self.sendEnd()
            log(
                "Archivo subido exitosamente con Go-Back-N.",
                logging.INFO,
                self.vrb,
            )
            self.queue.put(b"FINISHED")

        except FileNotFoundError:
            log(
                f"Error: El archivo {self.filename} no fue encontrado.",
                logging.ERROR,
                self.vrb,
            )

    def sendEnd(self):
        f_msg = "END".encode()
        dtgram = Datagram(header=f_msg.ljust(H_SIZE, b"\0"), data="-".encode())
        log("[→] Enviado END", logging.INFO, self.vrb)
        for _ in range(END_MAX_RETRIES):
            self.socket.sendto(dtgram.to_bytes(), self.srv_addr)
            try:
                raw_ack = self.queue.get(timeout=TIMEOUT_COEFFICIENT)
                ack_datagram = Datagram.from_bytes(raw_ack)
                ack_header = ack_datagram.header.decode().strip("\0")
                if ack_header == "END_ACK":
                    log("[✓] Recibido END_ACK", logging.INFO, self.vrb)
                    return
            except q.Empty:
                log(
                    "[!] Timeout esperando END_ACK, reenviando END",
                    logging.WARNING,
                    self.vrb,
                )
        log(
            "[!] No se recibió END_ACK tras varios intentos.",
            logging.ERROR,
            self.vrb,
        )

    def receive(self, queue):
        self.queue = queue
        log("Esperando archivo GBN", logging.INFO, self.vrb)
        endConection = 0
        expected_seq_number = 0
        l_ack = -1
        finish = False
        file_path = f"{self.destination}/{self.filename}"

        with open(file_path, "wb") as f:
            while True:
                try:
                    packet = self.queue.get(timeout=TIMEOUT_COEFFICIENT)
                    datagram = Datagram.from_bytes(packet)
                    header = datagram.header.decode().strip("\0")
                    log(f"Header recibido: {header}", logging.DEBUG, self.vrb)
                    if header.startswith("END"):
                        return self.sendEndAck()

                    if not header.startswith("DATA"):
                        log(
                            f"Ignorando mensaje de control: {header}",
                            logging.DEBUG,
                            self.vrb,
                        )
                        continue

                    parts = header.split(":")
                    try:
                        seq = int(parts[0].replace("DATA", ""))
                    except ValueError:
                        log(
                            f"Cabecera de datos inválida: {header}",
                            logging.WARNING,
                            self.vrb,
                        )
                        continue
                    log(f"[←] Recibido paquete {seq}", logging.DEBUG, self.vrb)
                    is_last = int(parts[1]) if len(parts) > 1 else 0

                    if seq == expected_seq_number:
                        f.write(datagram.data)
                        l_ack = seq
                        expected_seq_number += 1
                        self.socket.sendto(
                            f"ACK{l_ack}".encode(), self.srv_addr
                        )
                        log(
                            f"[✓] {P}{seq} recibido, enviado ACK{l_ack}",
                            logging.INFO,
                            self.vrb,
                        )

                        if is_last == 1:
                            packet = self.queue.get(timeout=GBN_MIN_TIMEO)
                            log(
                                "Recepción finalizada tras último paquete.",
                                logging.INFO,
                                self.vrb,
                            )
                    else:
                        if l_ack >= 0:
                            self.socket.sendto(
                                f"ACK{l_ack}".encode(), self.srv_addr
                            )
                            m = f"[!] {P} {seq} fuera de orden, "
                            m1 = f"reenviado ACK{l_ack}"
                            log(
                                m+m1,
                                logging.WARNING,
                                self.vrb,
                            )

                except q.Empty:
                    if finish:
                        log(
                            "Recepción finalizada tras último paquete.",
                            logging.INFO,
                            self.vrb,
                        )
                        break
                    else:
                        log("Esperando más paquetes", logging.DEBUG, self.vrb)
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

    def sendEndAck(self):
        f_msg = "END_ACK".encode()
        dgram = Datagram(header=f_msg.ljust(H_SIZE, b"\0"), data="-".encode())
        log("[✓] Enviado END_ACK", logging.INFO, self.vrb)
        for _ in range(END_MAX_RETRIES):
            self.socket.sendto(dgram.to_bytes(), self.srv_addr)
