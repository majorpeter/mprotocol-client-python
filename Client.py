import socket
from datetime import datetime
from threading import Thread, RLock, Event

from mprotocol_client_python.ProtocolResult import ProtocolResult
from mprotocol_client_python.NodeProperty import NodeProperty


def DEBUG_PRINT(message):
    print('[%s] %s' % (datetime.now().strftime('%H:%M:%S'), message))


## MProtocol client class
#
# Manages connection to the remote device and is the interface for data exchange
class Client:
    ## Creates TCP/IP connection to server
    # @param timeout blocking timeout for synchronous commands
    def __init__(self, ip_address, port, timeout=None):
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout

        self.socket = None
        self.thread = None
        self.lock = RLock()
        self.result = None
        self.received_str = ''
        self.receiving_multiline = False
        self.received_multilines = None
        self.response_received_or_error = Event()
        self.subscribed_nodes = {}
        self.subscription_lock = RLock()
        self.trace_rx_callback = None
        self.trace_tx_callback = None

        self.root = NodeProperty(client=self, sync=True)
        self.root_async = NodeProperty(client=self, sync=False)

        self.connect()

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.ip_address, self.port))

        self.thread = Thread(target=self.thread_function, daemon=True)
        self.thread.start()

    def set_trace_callbacks(self, rx_callback, tx_callback):
        self.trace_rx_callback = rx_callback
        self.trace_tx_callback = tx_callback

    ## Sends command without waiting for any response
    def send_async(self, command):
        with self.lock:
            if not self.socket:
                self.connect()

            if self.trace_tx_callback:
                self.trace_tx_callback(command)
            self.socket.send((command + '\n').encode('ascii'))

    ## Sends command and waits for response
    def send_sync(self, command):
        with self.lock:
            if not self.socket:
                self.connect()
            self.response_received_or_error.clear()
            self.result = None

            if self.trace_tx_callback:
                self.trace_tx_callback(command)
            self.socket.send((command + '\n').encode('ascii'))
            if not self.response_received_or_error.wait(self.timeout):
                self.socket.close()
                raise BaseException('Connection timed out (last command: %s)' % command)

            if not self.socket:
                raise BaseException('Socket destroyed (last command: %s)' % command)

            response = self.result
            return response

    ## Adds a new subscription to an asynchronous change message
    #
    # @note Also enables sending changes on the given node if it is the first subscription.
    def add_subscription(self, callback, node_path, property_name=None):
        send_open_command = False
        with self.subscription_lock:
            if node_path in self.subscribed_nodes.keys():
                item = self.subscribed_nodes[node_path]
            else:
                item = {}
                self.subscribed_nodes[node_path] = item
                send_open_command = True

            if property_name is None:
                property_name = ''

            if property_name in item.keys():
                item[property_name].append(callback)
            else:
                item[property_name] = [callback]

        if send_open_command:
            self.send_sync('OPEN ' + node_path)

    ## Removes a subscription for asynchronous change messages
    #
    # @note Also disables sending changes on the given node if it was the last subscription.
    def remove_subscription(self, callback, node_path, property_name=None):
        send_close_command = False
        with self.subscription_lock:
            if node_path in self.subscribed_nodes.keys():
                if property_name is None:
                    property_name = ''

                if property_name in self.subscribed_nodes[node_path]:
                    if callback in self.subscribed_nodes[node_path][property_name]:
                        self.subscribed_nodes[node_path][property_name].remove(callback)
                        if len(self.subscribed_nodes[node_path][property_name]) == 0:
                            del self.subscribed_nodes[node_path][property_name]
                            if len(self.subscribed_nodes[node_path]) == 0:
                                del self.subscribed_nodes[node_path]
                                send_close_command = True
        if send_close_command:
            self.send_sync('CLOSE ' + node_path)

    ## Background thread that handles incoming traffic
    def thread_function(self):
        DEBUG_PRINT('starting thread')
        while True:
            try:
                received_bytes = self.socket.recv(4096)
                if len(received_bytes) != 0:
                    self.received_str += received_bytes.decode('ascii')
                    self.process_received_str()
                else:
                    # recv() returns empty string if the remote side has closed the connection
                    DEBUG_PRINT('finishing thread (empty recv)')
                    break
            except Exception as e:
                # remote side will not be sending more data after connection errors
                DEBUG_PRINT('finishing thread (exception:%s)' % str(e))
                break

        # close and delete socket so that it won't be used again
        self.socket.close()
        self.socket = None

        # try to signal error to caller thread
        self.response_received_or_error.set()

    ## This function parses each incoming data segment
    def process_received_str(self):
        lines = self.received_str.split('\n')

        for i in range(0, len(lines) - 1):
            line = lines[i]
            if self.trace_rx_callback:
                self.trace_rx_callback(line)

            if self.receiving_multiline:
                if line != '}':
                    self.received_multilines.append(line)
                else:
                    self.result = ProtocolResult(ProtocolResult.ok_init_str, self.received_multilines)
                    self.response_received_or_error.set()

                    self.receiving_multiline = False
                    self.received_multilines = None
            elif ProtocolResult.is_valid_result(line):
                self.result = ProtocolResult(line)
                self.response_received_or_error.set()
            elif line == '{':
                self.receiving_multiline = True
                self.received_multilines = []
            elif line.startswith('CHG '):
                self.process_change(line)
            elif line.startswith('MAN '):
                self.result = ProtocolResult(ProtocolResult.ok_init_str, line[4:])
                self.response_received_or_error.set()
            else:
                DEBUG_PRINT('Unable to process response: ' + line)

        # keep last unfinished line in buffer
        self.received_str = lines[-1]

    ## This function processes incoming lines that are async. change messages
    # @param line change message (e.g. 'CHG <node_path>.<property>=<new_value>
    def process_change(self, line):
        # trim 'CHG '
        line = line[line.index(' ') + 1:]
        node_path = line[:line.index('.')]

        with self.subscription_lock:
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
