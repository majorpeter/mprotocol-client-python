import re
import socket
from threading import Thread, RLock, Event


class Client:
    def __init__(self, ip_address, port):
        self.ip_address = ip_address
        self.port = port

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = RLock()
        self.response_str = None
        self.received_str = ''
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
        self.response_str = None

        self.socket.send((command + '\n').encode('ascii'))
        self.response_received.wait()
        response = self.response_str

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

        #TODO is_multiline = False
        for i in range(0, len(lines) - 2):
            line = lines[i]
            if re.match('^E[0-9]:', line):
                self.response_str = line
                self.response_received.set()
            else:
                print('Unable to process response: ' + line)

        # keep last unfinished line
        self.received_str = lines[-1]
