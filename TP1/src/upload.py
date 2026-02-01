from socket import socket, AF_INET, SOCK_DGRAM
from lib.stopAndWait import SW
from lib.goBackN import GBN
from lib.client import Client
from lib.common import Action, log, MAX_FILE_SIZE
import sys
import os
import argparse
import logging

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


def main():

    p = argparse.ArgumentParser(description="< command description >")
    g = p.add_mutually_exclusive_group()
    g.add_argument("-v", "--verbose", action="store_true")
    g.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("-H", "--host", type=str, help="Server IP address")
    p.add_argument("-p", "--port", type=int, help="Server port")
    p.add_argument("-s", "--src", type=str, help="Source file path")
    p.add_argument("-n", "--name", type=str, help="File name")
    p.add_argument(
        "-r",
        "--protocol",
        type=str,
        help="Protocol error recovery protocol",
        required=True,
        choices=["SW", "GBN"],
    )

    args = p.parse_args()
    if not os.path.isfile(f"{args.src}/{args.name}"):
        print(f"El archivo {args.src}/{args.name} no existe.")
        sys.exit(1)
    file_size = os.path.getsize(f"{args.src}/{args.name}")
    if file_size > MAX_FILE_SIZE:
        print("El archivo excede el tamaño máximo permitido.")
        sys.exit(1)

    clientSocket = socket(AF_INET, SOCK_DGRAM)
    adr = (args.host, args.port)
    verbosity = "normal"
    if args.verbose:
        verbosity = "verbose"
    elif args.quiet:
        verbosity = "quiet"
    recovery = None
    match args.protocol:
        case "SW":
            log("Using Stop and Wait protocol", logging.INFO, verbosity)
            recovery = SW(clientSocket, adr, args.src, args.name, verbosity)
        case "GBN":
            log("Using Go-Back-N protocol", logging.INFO, verbosity)
            recovery = GBN(clientSocket, adr, args.src, args.name, verbosity)
        case _:
            log("Unknown protocol", logging.ERROR, verbosity)
            sys.exit(1)

    c = Client(clientSocket, adr, recovery, args.src, args.name, verbosity)
    c.start(Action.UPLOAD)


if __name__ == "__main__":
    main()
