import socket


class Error:
    def __init__(self, message):
        self.message = message


class RedisServer:
    def __init__(self, host="127.0.0.1", port=6379) -> None:
        self.host = host
        self.port = port
        self.data_storage = {}

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(f"Redis server listening on {self.host}: {self.port}")
            while True:
                client_socket, client_address = server_socket.accept()
                print(f"Accepted connection from {client_address}")
                self.handle_client(client_socket)

    def handle_client(self, client_socket):
        with client_socket:
            while True:
                command = client_socket.recv(1024)
                if not command:
                    break
                response = self.process_command(command)
                print(response)
                print(response.encode())
                client_socket.sendall(response.encode())

    def process_command(self, command):
        deserialized = self.deserialize_resp(command)
        if deserialized[0].lower() == "ping":
            return self.serialize_resp("PONG")
        elif deserialized[0].lower() == "echo":
            return self.serialize_resp(deserialized[1])
        elif deserialized[0].lower() == "get":
            data = self.data_storage.get(deserialized[1], "nil")
            return self.serialize_resp(data)
        elif deserialized[0].lower() == "set":
            key, value = deserialized[1], deserialized[2]
            self.data_storage[key] = value
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


redis_server = RedisServer()
redis_server.start()
