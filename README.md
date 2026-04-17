# COMP2322 Multi-threaded Web Server Project
Respository Name: web-server

(The Hong Kong Polytechnic University - COMP2322 Computer Networking)

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

1. Run the server script.
```text
python src/server.py
```

2. Open a web browser and navigate to `http://localhost:80` to check the server.

# Instruction to Test the Server

1. Use the provided test files in the `test_files` directory to test the server's response to various requests (e.g., `http://localhost:80/index.html` or `http://localhost:80/test_image.jpg`).

2. Use tools like `curl` or other tools to test different HTTP methods (`HEAD`).
```text
curl -I http://localhost:80/index.html
```

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
- [x] Multi-threaded Web server, each thread handles one HTTP request
- [ ] Proper request and response message exchanges
- [x] GET command for both text files and image files
- [x] HEAD command
- [ ] Five types of response statuses ONLY, including 200 OK, 400 Bad Request, 403 Forbidden, 404 File Not Found, 304 Not Modified
- [x] Handle Last-Modified and If-Modified-Since header fields
- [ ] Handle Connection header field for both HTTP persistent connection (keep-alive) and non-persistent connection (close) 
