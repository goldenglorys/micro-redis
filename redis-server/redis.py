import os
import pickle
import selectors
import socket
import time


class Error:
    def __init__(self, message):
        self.message = message


class RedisServer:
    def __init__(self, host="127.0.0.1", port=6379) -> None:
        self.host = host
        self.port = port
        self.data_storage = {}
        self.sel = selectors.DefaultSelector()


    def start(self):
        self.load_data()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            server_socket.setblocking(False)
            self.sel.register(server_socket, selectors.EVENT_READ, self.accept)
            print(f"Redis server listening on {self.host}: {self.port}")
            try:
                while True:
                    events = self.sel.select(timeout=None)
                    for key, mask in events:
                        callback = key.data
                        callback(key.fileobj, mask)
            except KeyboardInterrupt:
                print("Caught keyboard interrupt, exiting")


    def accept(self, sock, mask):
        client_socket, client_address = sock.accept()
        print(f"Accepted connection from {client_address}")
        client_socket.setblocking(False)
        self.sel.register(client_socket, selectors.EVENT_READ, self.handle_client)


    def handle_client(self, client_socket, mask):
        command = client_socket.recv(1024)
        if command:
            response = self.process_command(command)
            client_socket.sendall(response.encode())
        else:
            self.sel.unregister(client_socket)
            client_socket.close()
        with client_socket:
            while True:
                command = client_socket.recv(1024)
                if not command:
                    break
                response = self.process_command(command)
                client_socket.sendall(response.encode())


    def process_command(self, command):
        deserialized = self.deserialize_resp(command)
        if deserialized[0].lower() == "ping":
            return self.serialize_resp("PONG")
        elif deserialized[0].lower() == "echo":
            return self.serialize_resp(deserialized[1])
        elif deserialized[0].lower() == "exists":
            key = deserialized[1]
            return self.serialize_resp(1 if key in self.data_storage else 0)
        elif deserialized[0].lower() == "del":
            count = 0
            for key in deserialized[1:]:
                if key in self.data_storage:
                    del self.data_storage[key]
                    count += 1
            return self.serialize_resp(count)
        elif deserialized[0].lower() == "incr" or deserialized[0].lower() == "decr":
            key = deserialized[1]
            if key not in self.data_storage:
                return self.serialize_resp("nil")
            value, expiry = self.data_storage[key]
            if isinstance(value, int):
                self.data_storage[key] = (
                    value + 1 if deserialized[0].lower() == "incr" else value - 1,
                    expiry,
                )
                return self.serialize_resp(self.data_storage[key][0])
            else:
                return self.serialize_resp("value is not an integer")
        elif deserialized[0].lower() == "lpush" or deserialized[0].lower() == "rpush":
            key = deserialized[1]
            values = deserialized[2:]
            if key not in self.data_storage:
                self.data_storage[key] = (values, None)
            else:
                existing_values, expiry = self.data_storage[key]
                if not isinstance(existing_values, list):
                    return self.serialize_resp("existing value is not a list")
                if deserialized[0].lower() == "lpush":
                    values.extend(existing_values)
                else:
                    existing_values.extend(values)
                    values = existing_values
                self.data_storage[key] = (values, expiry)
            return self.serialize_resp(len(self.data_storage[key][0]))
        elif deserialized[0].lower() == "get":
            key = deserialized[1]
            value, expiry = self.data_storage.get(key, ("nil", None))
            if expiry is not None:
                if time.time() > expiry:
                    del self.data_storage[key]
                    return self.serialize_resp("nil")
            return self.serialize_resp(value)
        elif deserialized[0].lower() == "set":
            key, value = deserialized[1], deserialized[2]
            ex, px, exat, pxat = None, None, None, None
            if len(deserialized) > 3:
                for i in range(3, len(deserialized), 2):
                    option = deserialized[i].lower()
                    if option == "ex":
                        ex = int(deserialized[i + 1])
                    elif option == "px":
                        px = int(deserialized[i + 1]) / 1000
                    elif option == "exat":
                        exat = int(deserialized[i + 1])
                        ex = exat - int(time.time())
                    elif option == "pxat":
                        pxat = int(deserialized[i + 1])
                        px = (pxat - int(time.time() * 1000)) / 1000
            expiry = ex or px
            if expiry is not None:
                self.data_storage[key] = (value, time.time() + expiry)
            else:
                self.data_storage[key] = (value, None)
            return self.serialize_resp("OK")
        elif deserialized[0].lower() == "save":
            with open("dump.pkl", "wb") as f:
                pickle.dump(self.data_storage, f)
            return self.serialize_resp("OK")
        else:
            return self.serialize_resp("Invalid command")


    def serialize_resp(self, data):
        if data is None:
            return "$-1\r\n"
        elif isinstance(data, str):
            return f"${len(data)}\r\n{data}\r\n"
        elif isinstance(data, int):
            return f":{data}\r\n"
        elif isinstance(data, list):
            serialized_elements = "".join(self.serialize_resp(item) for item in data)
            return f"*{len(data)}\r\n{serialized_elements}"
        elif isinstance(data, Error):
            return f"-{data.message}\r\n"
        else:
            raise TypeError("Unsupported RESP type")


    def deserialize_resp(self, message):
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        if message.startswith("*"):
            parts = message[1:].split("\r\n")
            num_elements = int(parts[0])
            elements = []
            i = 1
            while num_elements > 0 and i < len(parts):
                if parts[i].startswith("$"):
                    length = int(parts[i][1:])
                    i += 1
                    elements.append(parts[i][:length])
                i += 1
                num_elements -= 1
            return elements
        elif message.startswith("$"):
            length = int(message[1 : message.index("\r\n")])
            if length == -1:
                return None
            start = message.index("\r\n") + 2
            end = start + length
            return message[start:end]
        elif message.startswith("+"):
            return message[1 : message.index("\r\n")]
        elif message.startswith("-"):
            return message[1 : message.index("\r\n")]
        elif message.startswith(":"):
            return int(message[1 : message.index("\r\n")])
        else:
            raise ValueError("Invalid RESP message")


    def load_data(self):
        if os.path.exists("dump.pkl"):
            with open("dump.pkl", "rb") as f:
                self.data_storage = pickle.load(f)


redis_server = RedisServer()
redis_server.start()
