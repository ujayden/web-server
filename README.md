# COMP2322 Multi-threaded Web Server Project

The Hong Kong Polytechnic University - COMP2322 Computer Networking

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

# Compile the source code

Since this project is written in Python, **no compilation** is required. You can run the source code directly.

# Environment Requirements
- Python 3.x (Minimum version: 3.6, Recommended version: 3.14.3)
- This project is written and tested on **Python 3.14.3**, on Windows 11 x64. It should also work on other platforms (Linux, macOS) with Python 3.x installed.
- No additional libraries are required, as it uses only standard Python libraries.

# Setup Instructions
1. Clone the repository to your local machine.
```text
git clone https://github.com/ujayden/web-server
cd web-server
```
2. Ensure the `test_files` directory is located in the project root directory, as the server will use it to serve files.

3. (Optional) If you want to change the server's root directory or other configurations, you can edit the constants defined at the beginning of `server.py`.

4. **Critical: On some systems, running a server on port 80 may require administrative privileges. If you encounter permission issues, consider changing the `SERVER_PORT` constant in `server.py` to a higher port number (e.g., 8080) that does not require special permissions.**

# Run the Server

1. Run the server script.
```text
python src/server.py
```

2. Open a web browser and navigate to `http://localhost:80` to check the server.

3. Adjust SERVER_PORT in `server.py` if you want to use a different port. The default port is set to 80, which is the standard port for HTTP, but it may cause permission issues on some systems. You can use a higher port number (e.g., 8080) if needed.

# Instruction to Test the Server

1. Use the provided test files in the `test_files` directory to test the server's response to various requests (e.g., `http://localhost:80/index.html` or `http://localhost:80/demo_image.jpeg`).

2. Use tools like `curl` or other tools to test different HTTP methods (`HEAD`).
```text
curl -I http://localhost:80/index.html
```

3. Quick tests with expected output

GET existing page
```text
curl -i http://localhost:80/index.html
```
Expected output (main lines):
```text
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: <number>
Last-Modified: <http date>
```

GET missing page
```text
curl -i http://localhost:80/not_found.html
```
Expected output:
```text
HTTP/1.1 404 File Not Found
Content-Type: text/plain
Content-Length: 14

File Not Found
```

HEAD request
```text
curl -I http://localhost:80/index.html
```
Expected output (main lines):
```text
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: <number>
Last-Modified: <http date>
```
Note: `HEAD` only returns headers, no body.

For more detailed test cases and expected outputs, please refer to `test-cases.md`.

# File Structure

```text
.
├─ README.md
├─ src
│  └─ server.py # Main server code 
├─ test_files # HTML & image files for testing
└─ server.log # Request log for client access and server responses
```

# Checklist
- [x] Multi-threaded Web server, each thread handles one HTTP request
- [x] Proper request and response message exchanges
- [x] GET command for both text files and image files
- [x] HEAD command
- [x] Five types of response statuses ONLY, including 200 OK, 400 Bad Request, 403 Forbidden, 404 File Not Found, 304 Not Modified
- [x] Handle Last-Modified and If-Modified-Since header fields
- [x] Handle Connection header field for both HTTP persistent connection (keep-alive) and non-persistent connection (close) 
- [x] A complete log file records the historical information about the client requests and server responses