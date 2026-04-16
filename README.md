# COMP2322 Multi-threaded Web Server Project
Respository Name: web-server

# Objective
This project aims to develop a socket program to implement a Web service using the HTTP protocol.

# Features
 
- Create a connection socket when contacted by a client (browser);
- Receive the HTTP request from this connection;
- Parse the request to determine the specific file being requested;
- Get the requested file from the server’s file system;
- Create an HTTP response message consisting of the requested file preceded by header lines;
- Send the response over the TCP connection to the requesting client. If the client requests a file that is not present in your server, your server should return a “404 Not Found” error message.

# Instruction to Run the Server

1. Clone the repository to your local machine.

```text
git clone https://github.com/ujayden/web-server.git
cd web-server
```

2. Run the server script.
```text
python src/server.py
```

3. Open a web browser and navigate to `http://localhost:80` to check the server.

# Instruction to Test the Server

(Currently, the server only returns a simple "Hello, World!" message for any request.)

# File Structure

```text
.
├─ README.md
├─ src
│  └─ server.py # Main server code 
└─ test_files # HTML & image files for testing
└─ server.log # Request log for client access and server responses
```

# Checklist
- [ ] Multi-threaded Web server, each thread handles one HTTP request
- [ ] Proper request and response message exchanges
- [ ] GET command for both text files and image files
- [ ] HEAD command
- [ ] Five types of response statuses ONLY, including 200 OK, 400 Bad Request, 403 Forbidden, 404 File Not Found, 304 Not Modified
- [ ] Handle Last-Modified and If-Modified-Since header fields
- [ ] Handle Connection header field for both HTTP persistent connection (keep-alive) and non-persistent connection (close) 
