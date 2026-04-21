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

Unsupported method (POST)
```text
curl -i -X POST http://localhost:80/index.html
```
Expected output:
```text
HTTP/1.1 400 Bad Request
Content-Type: text/plain
Content-Length: 11

Bad Request
```

Cache validation (304 - Not Modified)

Step A: get `Last-Modified`
```text
curl -I http://localhost:80/index.html
```

Step B: send `If-Modified-Since` with that same value
```text
curl -i http://localhost:80/index.html -H "If-Modified-Since: <paste Last-Modified here>"
```
Expected output (main lines):
```text
HTTP/1.1 304 Not Modified
Content-Length: 0
Last-Modified: <http date>
```

Cache validation with newer date (200)

Send `If-Modified-Since` with a future date to verify file was modified
```text
curl -i http://localhost:80/index.html -H "If-Modified-Since: Sun, 01 Jan 2023 00:00:00 GMT"
```
Expected output (main lines):
```text
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: <number>
Last-Modified: <http date>
```

Forbidden resource (403)

Request a file in the BLOCK_PATH_LIST
```text
curl -i http://localhost:80/forbidden.html
```
Expected output:
```text
HTTP/1.1 403 Forbidden
Content-Type: text/plain
Content-Length: 9

Forbidden
```

Root path "/" (auto-serving index.html)

Request the root path
```text
curl -i http://localhost:80/
```
Expected output (main lines):
```text
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: <number>
Last-Modified: <http date>
```
Note: With `ROOT_TO_INDEX_HTML = True` in server.py, "/" automatically serves "index.html"

Nested directory request

Request a file in a subdirectory
```text
curl -i http://localhost:80/folder/page_in_folder.html
```
Expected output (main lines):
```text
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: <number>
Last-Modified: <http date>
```

Different content types

Testing various file types supported by the server:

HTML file
```text
curl -i http://localhost:80/index.html
```

Another HTML file
```text
curl -i http://localhost:80/another_page.html
```

Both should return `Content-Type: text/html`

Multi-request persistent connection (HTTP/1.1 Keep-Alive)

Send multiple requests over the same connection (HTTP/1.1 default keep-alive)
```text
curl -i -w "\n" http://localhost:80/index.html http://localhost:80/another_page.html
```
Expected output:
- First response header includes `Connection: keep-alive` (or no Connection header in HTTP/1.1)
- Second response header also includes `Connection: keep-alive`
- Both requests use the same TCP connection

Or manually with netcat (bash/PowerShell):
```text
(echo -e "GET /index.html HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\nGET /another_page.html HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n") | nc localhost 80
```
Expected behavior: Both requests are answered before connection closes.

Close connection immediately (HTTP/1.1)

Request with `Connection: close` header
```text
curl -i -H "Connection: close" http://localhost:80/index.html
```
Expected output (main lines):
```text
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: <number>
Connection: close
```

HTTP/1.0 behavior (connection closes by default)

Send an HTTP/1.0 request without Keep-Alive
```text
curl -i --http1.0 http://localhost:80/index.html
```
Expected output (main lines):
```text
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: <number>
Connection: close
```
Note: HTTP/1.0 defaults to non-persistent (close) unless client explicitly sends `Connection: keep-alive`

HTTP/1.0 with Keep-Alive

Send an HTTP/1.0 request with explicit `Connection: keep-alive`
```text
curl -i --http1.0 -H "Connection: keep-alive" http://localhost:80/index.html
```
Expected output (main lines):
```text
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: <number>
Connection: keep-alive
Keep-Alive: timeout=5
```

Malformed request (400 Bad Request)

Send an invalid request line (missing HTTP version)
```text
echo -e "GET /index.html\r\n\r\n" | nc localhost 80
```
Or
```text
printf "GET /index.html\r\n\r\n" | nc localhost 80
```
Expected output:
```text
HTTP/1.1 400 Bad Request
Content-Type: text/plain
Content-Length: 11

Bad Request
```

Access log verification

Check that the server is logging requests properly
```text
cat server.log
```
Expected output format (each line represents a request):
```text
<client_ip> - <client_port> [<timestamp>] "<method> <path> <http_version>" <status_code> <content_length> "<connection_mode>" "<user_agent>"
```
Example entries:
```text
127.0.0.1 - <port> [21/Apr/2026:10:15:30 +0800] "GET /index.html HTTP/1.1" 200 1234 "keep-alive" "curl/7.68.0"
127.0.0.1 - <port> [21/Apr/2026:10:15:35 +0800] "GET /not_found.html HTTP/1.1" 404 14 "close" "curl/7.68.0"
127.0.0.1 - <port> [21/Apr/2026:10:15:40 +0800] "GET /forbidden.html HTTP/1.1" 403 9 "close" "curl/7.68.0"

## Additional test cases

The following tests cover edge cases and security-related behaviors not included above.

- Path traversal (must not allow access outside `test_files`)

```text
curl -i --path-as-is http://localhost:80/../src/server.py
```
Expected output:
```text
HTTP/1.1 403 Forbidden
Content-Type: text/plain
Content-Length: 9

Forbidden
```

- Directory requests (requesting a directory should not return a directory listing)

```text
curl -i http://localhost:80/folder
curl -i http://localhost:80/folder/
```
Expected output:
```text
HTTP/1.1 404 File Not Found
Content-Type: text/plain
Content-Length: 14

File Not Found
```

- Query string handling (server treats query as part of filename)

```text
curl -i 'http://localhost:80/index.html?x=1'
```
Expected output (current server behavior):
```text
HTTP/1.1 404 File Not Found
```
Note: Typical web servers strip the query string and return `200 OK` for `index.html`.

- Percent-encoded paths (server does not decode percent-encoding)

```text
curl -i --path-as-is "http://localhost:80/%2e%2e/src/server.py"
```
Expected output:
```text
HTTP/1.1 404 File Not Found
```

- Missing `Host` header (HTTP/1.1) — server should not crash

```text
printf "GET /index.html HTTP/1.1\r\n\r\n" | nc localhost 80
```
Expected output (current server behavior):
```text
HTTP/1.1 200 OK
```

- Invalid `If-Modified-Since` format (should be ignored)

```text
curl -i -H "If-Modified-Since: invalid-date" http://localhost:80/index.html
```
Expected output:
```text
HTTP/1.1 200 OK
```

- `HEAD` for missing resource (headers-only)

```text
curl -I http://localhost:80/not_found.html
```
Expected output:
```text
HTTP/1.1 404 File Not Found
Content-Type: text/plain
Content-Length: 14
```

- Connection header precedence (presence of `close` should close connection)

```text
curl -i -H "Connection: keep-alive, close" http://localhost:80/index.html
```
Expected behavior: connection closed; response includes `Connection: close`.

- Keep-alive timeout behavior (server closes idle persistent connection after timeout)

```bash
(echo -e "GET /index.html HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"; sleep 6; echo -e "GET /index.html HTTP/1.1\r\nHost: localhost\r\n\r\n") | nc localhost 80
```
Expected behavior: first request returns `200 OK`; the second request fails because the server closed the connection after the keep-alive timeout (~5s).

- Concurrency / multithreading

```bash
for i in {1..20}; do curl -s http://localhost:80/index.html & done; wait
```
Expected behavior: server serves concurrent requests (mostly `200 OK`) without crashing.

- Binary image GET (if an image exists in `test_files`)

```text
curl -i http://localhost:80/demo_image.jpeg -o /dev/null
```
Expected output:
```text
HTTP/1.1 200 OK
Content-Type: image/jpeg
Content-Length: <number>
```
```