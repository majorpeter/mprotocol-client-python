import socket
from threading import Thread, RLock, Event

from mprotocol_client_python.ProtocolResult import ProtocolResult
from mprotocol_client_python.NodeProperty import NodeProperty


class Client:
    def __init__(self, ip_address, port, timeout=None):
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = RLock()
        self.result = None
        self.received_str = ''
        self.receiving_multiline = False
        self.received_multilines = None
        self.response_received = Event()
        self.subscribed_nodes = {}
        self.subscription_lock = RLock()

        self.root = NodeProperty(self)

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
        if not self.response_received.wait(self.timeout):
            raise BaseException('Connection timed out (last command: %s)' % command)
        response = self.result

        self.lock.release()
        return response

    def add_subscription(self, callback, node_path, property_name=None):
        self.subscription_lock.acquire()

        if node_path in self.subscribed_nodes.keys():
            item = self.subscribed_nodes[node_path]
        else:
            item = {}
            self.subscribed_nodes[node_path] = item
            self.send_sync('OPEN ' + node_path)

        if property_name is None:
            property_name = ''

        if property_name in item.keys():
            item[property_name].append(callback)
        else:
            item[property_name] = [callback]

        self.subscription_lock.release()

    def remove_subscription(self, callback, node_path, property_name=None):
        self.subscription_lock.acquire()

        if node_path in self.subscribed_nodes.keys():
            if property_name is None:
                property_name = ''

            if property_name in self.subscribed_nodes[node_path]:
                if callback in self.subscribed_nodes[node_path][property_name]:
                    self.subscribed_nodes[node_path][property_name].remove(callback)
                    if len(self.subscribed_nodes[node_path][property_name]) == 0:
                        del self.subscribed_nodes[node_path][property_name]
                        if len(self.subscribed_nodes[node_path]) == 0:
                            self.send_sync('CLOSE ' + node_path)
                            del self.subscribed_nodes[node_path]

        self.subscription_lock.release()

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
            elif line.startswith('CHG '):
                self.process_change(line)
            else:
                print('Unable to process response: ' + line)

        # keep last unfinished line in buffer
        self.received_str = lines[-1]

    def process_change(self, line):
        # trim 'CHG '
        line = line[line.index(' ') + 1:]
        node_path = line[:line.index('.')]

        self.subscription_lock.acquire()

        if node_path in self.subscribed_nodes.keys():
            subscribed_node = self.subscribed_nodes[node_path]

            prop = line[line.index('.') + 1:line.index('=')]
            value = line[line.index('=')+1:]

            # look for an exact matching property subscription
            if prop in subscribed_node.keys():
                for callback in subscribed_node[prop]:
                    callback(prop, value)

            # send to node subscription if available
            if '' in subscribed_node.keys():
                for callback in subscribed_node['']:
                    callback(prop, value)

        self.subscription_lock.release()