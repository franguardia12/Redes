from socket import socket, AF_INET, SOCK_DGRAM
import argparse
from lib.server import Server
from lib.common import log
import logging


def main():
    p = argparse.ArgumentParser(description="< command description >")
    g = p.add_mutually_exclusive_group()
    g.add_argument(
        "-v",
        "--verbose",
        action="store_true",
    )
    g.add_argument(
        "-q",
        "--quiet",
        action="store_true",
    )
    p.add_argument("-H", "--host", type=str, help="Server IP address")
    p.add_argument("-p", "--port", type=int, help="Server port")
    p.add_argument("-n", "--name", type=str, help="File name")
    p.add_argument(
        "-s", "--storage", type=str, help="Str directory path", required=True
    )

    args = p.parse_args()
    serverSocket = socket(AF_INET, SOCK_DGRAM)
    adr = (args.host, args.port)
    serverSocket.bind(adr)

    verbosity = "normal"
    if args.verbose:
        verbosity = "verbose"
    elif args.quiet:
        verbosity = "quiet"
    log(
        f"Iniciando servidor en {adr}",
        logging.INFO,
        verbosity,
    )
    log("Presiona 'q' y luego Enter para apagarlo", logging.INFO, verbosity)
    server = Server(adr, serverSocket, args.storage, verbosity)
    server.start()


if __name__ == "__main__":
    main()
