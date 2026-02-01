from lib.common import H_SIZE


class Datagram:
    def __init__(self, header: bytes, data: bytes):
        self.header = header
        self.data = data

    def to_bytes(self):
        return self.header + self.data

    def from_bytes(data: bytes):
        header = data[:H_SIZE]
        payload = data[H_SIZE:]
        return Datagram(header, payload)
