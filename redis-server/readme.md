## A Simple Redis Server Implementation

This Python script implements a simple Redis server that supports a subset of Redis commands and uses the selectors module to handle multiple concurrent clients. The server uses a dictionary to store key-value pairs and supports commands like PING, ECHO, GET, SET, EXISTS, DEL, INCR, DECR, LPUSH, RPUSH, and SAVE. The SET command also supports optional parameters for setting an expiry time for the key-value pair.

### Class Definitions

### Error
```python
class Error:
    def __init__(self, message):
        """Initialize an Error with a given message."""
        self.message = message
```
The `Error` class is used to represent error messages that can be returned to the client.

### RedisServer
The RedisServer class encapsulates the functionality of a Redis server. It initializes with a host and port for the server to listen on and uses a dictionary for data storage and selector object for handling multiple concurrent clients.

`__init__(self, host="127.0.0.1", port=6379)`

This is the constructor of the RedisServer class. It initializes a new instance of the class. The `host` and `port` parameters specify the network address where the server will listen for incoming connections. The default address is `127.0.0.1:6379`.

### Methods

`start(self)`
This method starts the server. It first loads any saved data from disk, then creates a socket and starts listening for incoming connections. It registers the accept method with the selector to handle new connections.

`accept(self, sock, mask)`
The `accept` method is called by the selector when a new connection is ready to be accepted. It sets up the client socket and registers the handle_client method with the selector to handle client communication.

> Note: There are many approaches to concurrency. A popular approach is to use Asynchronous I/O. The traditional choice is to use threads. However, this implementation use something that’s even more traditional than threads and easier to reason about. It's the granddaddy of system calls: `.select()`. By using the `selectors` module (built upon the select module) in the standard library, the most efficient implementation is used, regardless of the operating system this happen to be running on.
`asyncio` uses single-threaded cooperative multitasking and an event loop to manage tasks. With `.select()`, own version of an event loop was written, albeit more simply and synchronously.

`handle_client(self, client_socket, mask)`
The `handle_client` method reads commands from the client, processes them using the `process_command` method, and sends back responses. If the client disconnects, it unregisters the client socket and closes it.

`process_command(self, command)`
The `process_command` method deserializes the command received from the client and executes the corresponding Redis command and returns the serialized response. It supports commands like PING, ECHO, EXISTS, DEL, INCR, DECR, LPUSH, RPUSH, GET, SET, and SAVE.

`serialize_resp(self, data)`
The `serialize_resp` method converts Python data types into the Redis Serialization Protocol (RESP) format for sending responses to the client.

`deserialize_resp(self, message)`
The `deserialize_resp` method converts RESP messages received from the client into a Python object for processing.

`load_data(self)`
The `load_data` method loads the server's data from a file on disk if it exists. This allows the server to restore its state when restarted.

### Example Usage 
To start the server, create an instance of the RedisServer class and call its start method:

```python
redis_server = RedisServer()
redis_server.start()
```
To connect to the server and send commands, you can use a Redis client. Here are some examples of how to use the supported commands:
- PING: `PING` - Checks if the server is alive.
- ECHO: `ECHO <message>` - Echoes the message back to the client.
- GET: `GET <key>` - Retrieves the value of a key.
- SET: `SET <key> <value> [EX <seconds>] [PX <milliseconds>] [EXAT <timestamp>] [PXAT <timestamp>]` - Sets the value of a key, optionally with an expiry time.
- EXISTS: `EXISTS <key>` - Checks if a key exists in the data storage.
- DEL: `DEL <key1> <key2> ...` - Deletes one or more keys.
- INCR: `INCR <key>` - Increments the integer value of a key by one.
- DECR: `DECR <key>` - Decrements the integer value of a key by one.
- LPUSH: `LPUSH <key> <value1> <value2> ...` - Inserts values at the head of a list.
- RPUSH: `RPUSH <key> <value1> <value2> ...` - Inserts values at the tail of a list.
- SAVE: `SAVE` - Saves the current state of the data storage to disk.

Please note that these commands should be sent in the RESP format. For example, the SET command would be sent as: `*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n$5\r\nvalue\r\n`.