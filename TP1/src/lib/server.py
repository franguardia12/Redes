import os
from queue import Queue
from threading import Thread
from lib.datagram import Datagram
from lib.goBackN import GBN
from lib.stopAndWait import SW
from lib.common import MAX_FILE_SIZE, log, H_SIZE, MSS
import logging
import sys
import select


class Server:
    def __init__(self, address, socket, storage, verbosity):
        self.address = address
        self.socket = socket
        self.storage = storage
        self.queues = {}
        self.verbosity = verbosity

    def start(self):
        try:
            while True:
                ready, _, _ = select.select([self.socket, sys.stdin], [], [])
                for r in ready:
                    if r == self.socket:
                        data, client_addr = self.socket.recvfrom(MSS + H_SIZE)
                        ms = f"Recibiendo data de {client_addr}"
                        log(
                            ms,
                            logging.INFO,
                            self.verbosity,
                        )
                        if client_addr not in self.queues:
                            self.new_client(client_addr, data)
                        else:
                            self.queues[client_addr].put(data)
                    elif r == sys.stdin:
                        user_input = sys.stdin.readline().strip()
                        if user_input.lower() == "q":
                            log(
                                "Cerrando servidor por solicitud del usuario",
                                logging.INFO,
                                self.verbosity,
                            )
                            self.socket.close()
                            return
        except TimeoutError:
            pass
        except KeyboardInterrupt:
            log("Cerrando servidor...", logging.INFO, self.verbosity)
            self.socket.close()

    def new_client(self, client_addr, first_message):
        log(f"Nuevo cliente desde {client_addr}", logging.INFO, self.verbosity)
        self.queues[client_addr] = Queue()
        self.queues[client_addr].put(first_message)
        client_thread = Thread(
            target=self.handle_client, args=(client_addr,), daemon=True
        )
        client_thread.start()

    def handle_client(self, client_addr):
        log(f"Atendiendo cliente: {client_addr}", logging.INFO, self.verbosity)
        queue = self.queues[client_addr]
        while True:
            data = queue.get()
            datagram = Datagram.from_bytes(data)
            payload = datagram.data.decode().strip("\0")

            msg = payload.split(" ")
            if msg[0] == "-" or msg[0] == "":
                break

            log(
                f"Recibiendo mensaje inicial de {client_addr}: {payload}",
                logging.INFO,
                self.verbosity,
            )
            log(f"Mensaje parseado: {msg}", logging.INFO, self.verbosity)
            recovery = None

            match msg[0]:
                case "SW":
                    log(
                        f"Cliente {client_addr} seleccionó el protocolo SW",
                        logging.INFO,
                        self.verbosity,
                    )
                    recovery = SW(
                        self.socket,
                        (client_addr[0], client_addr[1]),
                        self.storage,
                        "downloaded_file",
                        self.verbosity,
                    )
                case "GBN":
                    log(
                        f"Cliente {client_addr} seleccionó el protocolo GBN",
                        logging.INFO,
                        self.verbosity,
                    )
                    recovery = GBN(
                        self.socket,
                        (client_addr[0], client_addr[1]),
                        self.storage,
                        "downloaded_file",
                        self.verbosity,
                    )
                case _:
                    log(
                        f"Protocolo desconocido del cliente {client_addr}",
                        logging.ERROR,
                        self.verbosity,
                    )
                    return

            match msg[1:]:
                case ["UPLOAD", fname]:
                    log(
                        f"Atendiendo subida para {fname}",
                        logging.INFO,
                        self.verbosity,
                    )
                    self.handle_upload(queue, client_addr, fname, recovery)
                case ["DOWNLOAD", fname]:
                    log(
                        f"Atendiendo bajada para {fname}",
                        logging.INFO,
                        self.verbosity,
                    )
                    self.handle_download(queue, client_addr, fname, recovery)
                case _:
                    log(
                        f"Acción desconocida del cliente {client_addr}",
                        logging.ERROR,
                        self.verbosity,
                    )
                    return

    def handle_upload(self, queue, client_addr, filename, recovery):
        ack_message = f"ACK{0}".encode()
        datagram = Datagram(header=b"\x00" * H_SIZE, data=ack_message)
        self.socket.sendto(datagram.to_bytes(), client_addr)
        recovery.setFilename(filename)
        recovery.receive(self.queues[client_addr])

    def handle_download(self, queue, client_addr, filename, recovery):
        if not os.path.isfile(f"{self.storage}/{filename}"):
            log(
                f"Archivo {filename} no encontrado",
                logging.ERROR,
                self.verbosity,
            )
            e_msg = "ERROR Archivo no encontrado".encode()
            datagram = Datagram(header=b"\x00" * H_SIZE, data=e_msg)
            self.socket.sendto(datagram.to_bytes(), client_addr)
            return

        file_size = os.path.getsize(f"{self.storage}/{filename}")
        if file_size > MAX_FILE_SIZE:
            log(
                f"Archivo {filename} excede el tamaño máximo",
                logging.ERROR,
                self.verbosity,
            )
            e_msg = "ERROR Archivo demasiado grande".encode()
            datagram = Datagram(header=b"\x00" * H_SIZE, data=e_msg)
            self.socket.sendto(datagram.to_bytes(), client_addr)
            return

        ack_message = f"ACK{0}".encode()
        datagram = Datagram(header=b"\x00" * H_SIZE, data=ack_message)
        self.socket.sendto(datagram.to_bytes(), client_addr)
        recovery.setFilename(filename)
        recovery.send(self.queues[client_addr])
