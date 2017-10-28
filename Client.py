import re
import socket
from threading import Thread, RLock, Event

from mprotocol_client_python.ProtocolResult import ProtocolResult


class Client:
    def __init__(self, ip_address, port):
        self.ip_address = ip_address
        self.port = port

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = RLock()
        self.result = None
        self.received_str = ''
        self.receiving_multiline = False
        self.received_multilines = None
        self.response_received = Event()

        self.connect()

        self.thread = Thread(target=self.thread_function, daemon=True)
        self.thread.start()

    def connect(self):
        self.socket.connect((self.ip_address, self.port))

    def send_async(self, command):
        self.lock.acquire()
        self.socket.send((command + '\n').encode('ascii'))
        self.lock.release()

    def send_sync(self, command):
        self.lock.acquire()

        self.response_received.clear()
        self.result = None

        self.socket.send((command + '\n').encode('ascii'))
        self.response_received.wait()
        response = self.result

        self.lock.release()
        return response

    def thread_function(self):
        while True:
            received_bytes = self.socket.recv(4096)
            if len(received_bytes) != 0:
                self.received_str += received_bytes.decode('ascii')
                self.process_received_str()

    def process_received_str(self):
        lines = self.received_str.split('\n')

        for i in range(0, len(lines) - 1):
            line = lines[i]
            if self.receiving_multiline:
                if line != '}':
                    self.received_multilines.append(line)
                else:
                    self.result = ProtocolResult(ProtocolResult.ok_init_str, self.received_multilines)
                    self.response_received.set()

                    self.receiving_multiline = False
                    self.received_multilines = None
            elif ProtocolResult.is_valid_result(line):
                self.result = ProtocolResult(line)
                self.response_received.set()
            elif line == '{':
                self.receiving_multiline = True
                self.received_multilines = []
            else:
                print('Unable to process response: ' + line)

        # keep last unfinished line
        self.received_str = lines[-1]
