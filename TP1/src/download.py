import sys
from socket import socket, AF_INET, SOCK_DGRAM
import argparse
from lib.client import Client
from lib.stopAndWait import SW
from lib.goBackN import GBN
import logging
from lib.common import Action
from lib.common import log


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
    p.add_argument("-d", "--dst", type=str, help="Destination file path")
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

    clientSocket = socket(AF_INET, SOCK_DGRAM)
    adr = (args.host, args.port)
    vrb = "normal"
    if args.verbose:
        vrb = "verbose"
    elif args.quiet:
        vrb = "quiet"
    recovery = None
    match args.protocol:
        case "SW":
            log("Using Stop and Wait protocol", logging.INFO, vrb)
            recovery = SW(clientSocket, adr, args.dst, args.name, vrb)
        case "GBN":
            log("Using Go-Back-N protocol", logging.INFO, vrb)
            recovery = GBN(clientSocket, adr, args.dst, args.name, vrb)
        case _:
            log("Unknown protocol", logging.ERROR, vrb)
            sys.exit(1)
    client = Client(clientSocket, adr, recovery, args.dst, args.name, vrb)
    client.start(Action.DOWNLOAD)


if __name__ == "__main__":
    main()
