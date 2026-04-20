import socket # Basic socket library for TCP/IP communication
import threading # For Multi-threaded Web Server
import os 
from datetime import datetime, timezone

# CONFIGURATION
SERVER_HOST = '0.0.0.0'  # Listen IP -> 0.0.0.0: All
SERVER_PORT = 80         # Standard HTTP port
SERVER_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__)) # src/server.py
SERVER_ROOT_DIR = os.path.join(os.path.dirname(SERVER_SOURCE_DIR), 'test_files') # Go one level up, then test_files/
ROOT_TO_INDEX_HTML = True # True: For "/" request -> "index.html", False: For "/" request -> 404
LOG_LEVEL = 2            # 0: No logs, 1: Basic logs, 2: Detailed logs
ACCESS_LOG_FILE = 'server.log'  # Records the historical information about the client requests and server responses
KEEP_ALIVE_TIMEOUT_SECONDS = 5  # Timeout for idle persistent connections
QUEUE_TCP_CONNECTIONS = 10 # Number of TCP connections to queue (for listen())

STATUS_MESSAGES = {
    200: "OK",
    400: "Bad Request",
    403: "Forbidden",
    404: "File Not Found",
    304: "Not Modified"
}

CONTENT_TYPE_MAPPING = {
    # Support HTML and Image required for Project requirements. Other file type is for completeness as a general web server.
    # I hope it won't down my grade. (?)
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.txt': 'text/plain',
    'default': 'application/octet-stream'
    }
# END OF CONFIGURATION

# LOGGING FUNCTIONS
def log_console(message, always_print=False):
    if LOG_LEVEL >= 2 or always_print:
        print(f"[LOG] {message}")

def warn_console(message):
    if LOG_LEVEL >= 1:
        print(f"[WARN] {message}")
# END OF LOGGING FUNCTIONS

# FILE IO FUNCTIONS
def read_file(file_path):
    """
    Read file (support Binary) from spectific path, the return is the content of the file and do not modified. 
    [!] FileNotFoundError does not print in console. Since we dont have 500, it will assume **404** in future step.
    @param file_path: The path of the file to be read.
    @return: Tuple (success, content) where success is a boolean indicating if the file was read successfully, and content is the file content if successful, or None if not.
    """
    try:
        # Safety check
        if os.path.commonpath([SERVER_ROOT_DIR, file_path]) != SERVER_ROOT_DIR:
            raise Exception("Attempt to access file outside of root directory.")
        
        with open(file_path, 'rb') as file:
            return True, file.read()
    except FileNotFoundError:
        return False, None
    except Exception as e:
        warn_console(f"Error reading file {file_path}: {e}")
        return False, None

def generate_content_type(file_path):
    """
    Generate the Content-Type header value based on the file extension of the requested resource.
    @param file_path: Path of the requested file.
    @return: The appropriate Content-Type string for the HTTP response header.
    """
    _, ext = os.path.splitext(file_path)
    return CONTENT_TYPE_MAPPING.get(ext, CONTENT_TYPE_MAPPING['default'])

def format_http_datetime(dt):
    """
    Format datetime object to IMF-fixdate used by HTTP headers.
    @param dt: datetime object
    @return: HTTP-date string in GMT
    """
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

def parse_http_datetime(http_datetime):
    """
    Parse IMF-fixdate HTTP datetime string.
    @param http_datetime: value of If-Modified-Since header
    @return: timezone-aware datetime in UTC, or None if parse fails
    """
    try:
        return datetime.strptime(http_datetime, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

def get_last_modified_datetime(file_path):
    """
    Read file modification time and convert to UTC datetime (whole-second)
    @param file_path: path of target file
    @return: timezone-aware datetime in UTC, or None if metadata is unavailable
    """
    try:
        # HTTP-date only has second precision, so drop fractional seconds.
        return datetime.fromtimestamp(int(os.path.getmtime(file_path)), tz=timezone.utc)
    except OSError as e:
        warn_console(f"Unable to read mtime for {file_path}: {e}")
        return None

def generate_respond_headers(headers_dict):
    """
    Generate the HTTP response headers string from a dictionary of header key-value pairs.
    @param headers_dict: Header Dict
    @return: Formatted HTTP response headers string
    """
    return ''.join(f"{key}: {value}\r\n" for key, value in headers_dict.items())

def keep_alive_checker(version, request_headers):
    """
    Decide whether to keep the TCP connection keep-alive based on HTTP version and Connection header.
    @param version: HTTP version string from request line
    @param request_headers: Request header dictionary
    @return: True if connection should be kept alive, otherwise False
    """
    # Get Connection header value
    connection_header = request_headers.get('connection', '')
    # Generate a set when client send any comma-separated list of HTTP headers, meet HTTP standard
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Connection
    connection_header_set = {item.strip().lower() for item in connection_header.split(',') if item.strip()}

    # HTTP/1.1 defaults to keep-alive; HTTP/1.0 defaults to close.
    if version == 'HTTP/1.1':
        return 'close' not in connection_header_set # Return TRUE if not 'close' by client
    if version == 'HTTP/1.0':
        return 'keep-alive' in connection_header_set # Return TRUE if 'keep-alive' by client
    return False

def add_connection_headers(response_headers, connection_mode):
    """
    Add Connection headers to response headers.
    @param response_headers: Response header dictionary to modify in-place
    @param connection_mode: 'keep-alive' or 'close'
    """
    response_headers["Connection"] = connection_mode
    if connection_mode == 'keep-alive':
        response_headers["Keep-Alive"] = f"timeout={KEEP_ALIVE_TIMEOUT_SECONDS}"

def handle_request(method, path, version, request_headers, connection_mode='close'):
    """
    Handle incoming HTTP request and craft appropriate HTTP response.
    @param method: HTTP method (ONLY GET, HEAD)
    @param path: Requested resource path
    @param version: HTTP version (e.g., HTTP/1.1)
    @param headers: Dictionary of HTTP headers
    @param connection_mode: Connection response mode ('keep-alive' or 'close')
    @return: Formatted HTTP response, ready to be sent back to the client.
    """
    
    # First, we need to check if the method is supported (GET or HEAD)
    if method not in ['GET', 'HEAD']:
        warn_console(f"Unsupported HTTP method: {method}")
        response = generate_error_response(400, method, connection_mode)  # Bad Request for unsupported methods
        return response

    # Then, process path and try to serve the requested file
    if path == '/' and ROOT_TO_INDEX_HTML:
        file_path = os.path.join(SERVER_ROOT_DIR, 'index.html')
    elif path == '/' and not ROOT_TO_INDEX_HTML:
        warn_console(f"Root path '/' requested but ROOT_TO_INDEX_HTML is set to False.")
        response = generate_error_response(404, method, connection_mode)
        return response
    else:
        file_path = os.path.join(SERVER_ROOT_DIR, path.lstrip('/'))
 
    success, content = read_file(file_path)
    # Since no 500, success = False is treated as 404
    if not success:
        warn_console(f"File not found or IO error: {file_path}")
        response = generate_error_response(404, method, connection_mode)  # File Not Found
        return response

    # Handelling "If-Modified-Since" header for cache validation
    last_modified_dt = get_last_modified_datetime(file_path)
    if_modified_since_value = request_headers.get('if-modified-since')
    if if_modified_since_value and last_modified_dt is not None:
        if_modified_since_dt = parse_http_datetime(if_modified_since_value)
        # Invalid date format is ignored by sending normal 200 response.
        if if_modified_since_dt is not None and last_modified_dt <= if_modified_since_dt:
            response_headers = {
                "Content-Length": "0",
                "Last-Modified": format_http_datetime(last_modified_dt)
            }
            add_connection_headers(response_headers, connection_mode)
            first_line = f"HTTP/1.1 304 Not Modified\r\n"
            header_part = generate_respond_headers(response_headers)
            return first_line + header_part + "\r\n"

    # Identify the content type based on file extension
    content_type = generate_content_type(file_path)

    # Craft the HEADER of the response
    response_headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(content)) # For "Proper response message exchange" and avoid long loading time, 
    }
    if last_modified_dt is not None:
        response_headers["Last-Modified"] = format_http_datetime(last_modified_dt)
    add_connection_headers(response_headers, connection_mode)
    # since read mode is rb, content = bytes, len(content) = byte size of the file, which = correct value for Content-Length header.

    first_line = f"HTTP/1.1 200 OK\r\n"
    header_part = generate_respond_headers(response_headers)
    # IF method is HEAD, we only return the header without the body
    response = first_line + header_part + "\r\n"
    if method == 'GET':
        response = response.encode() + content
    return response

def generate_error_response(status_code, method='GET', connection_mode='close'):
    """
    Generate general HTTP error response based on the status code provided. If the status code is not recognized, defaults is "Unknown Error".
    @param status_code: HTTP status code (e.g., 400, 403, 404)
    @param method: HTTP method (default: 'GET'), used to determine if the response should include a body (False for HEAD requests - RFC 9110)
    @param connection_mode: Connection response mode ('keep-alive' or 'close')
    @return: Formatted HTTP response string with the appropriate status message and content.
    """
    status_message = STATUS_MESSAGES.get(status_code, "Unknown Error")
    body = status_message

    response_headers = {
        "Content-Type": "text/plain",
        "Content-Length": str(len(body))
    }
    add_connection_headers(response_headers, connection_mode)

    first_line = f"HTTP/1.1 {status_code} {status_message}\r\n"
    header_part = generate_respond_headers(response_headers)
    response = first_line + header_part + "\r\n"

    if method != 'HEAD':
        response = response + body

    return response

def read_raw_http_request(client_connection, request_buffer):
    """
    Read from RAW TCP socket until a complete HTTP header block is received.
    @param client_connection: Socket connected to client
    @param request_buffer: Buffered bytes from previous reads
    @return: Tuple (request_header_bytes or None, updated_buffer)
    """
    # Keep reading until end of the HTTP header block (indicated by \r\n\r\n)
    while b'\r\n\r\n' not in request_buffer:
        chunk = client_connection.recv(4096)
        if not chunk:
            return None, b''
        request_buffer += chunk

    raw_request, request_buffer = request_buffer.split(b'\r\n\r\n', 1)
    return raw_request, request_buffer

def parse_http_request(raw_request):
    """
    Parse request line and headers from raw HTTP bytes.
    @param raw_request: Raw request header bytes
    @return: Tuple (method, path, version, headers) or (None, None, None, None)
    """
    try:
        # ISO-8859-1: https://datatracker.ietf.org/doc/html/rfc5987 > Introduction
        request_text = raw_request.decode('iso-8859-1')
    except UnicodeDecodeError:
        return None, None, None, None

    request_info = request_text.split('\r\n')
    if len(request_info) == 0:
        return None, None, None, None

    try:
        method, path, version = request_info[0].split()
    except ValueError:
        return None, None, None, None

    headers = {}
    for line in request_info[1:]:
        if not line:
            continue
        if ': ' in line:
            key, value = line.split(': ', 1)
        elif ':' in line:
            key, value = line.split(':', 1)
        else:
            continue
        # Normalize to lower-case for case-insensitive HTTP header lookup.
        headers[key.strip().lower()] = value.strip()

    return method, path, version, headers

def handle_client(client_connection, client_address):
    try:
        client_connection.settimeout(KEEP_ALIVE_TIMEOUT_SECONDS)
        request_buffer = b''

        while True:
            raw_request, request_buffer = read_raw_http_request(client_connection, request_buffer)
            if raw_request is None:
                break

            method, path, version, headers = parse_http_request(raw_request)
            if method is None:
                warn_console(f"Received malformed request from {client_address} - Invalid request line")
                response = generate_error_response(400, connection_mode='close')
                client_connection.sendall(response.encode())
                break

            # Early check if the method is supported
            is_supported_method = method in ['GET', 'HEAD']
            keep_alive = keep_alive_checker(version, headers) and is_supported_method
            connection_mode = 'keep-alive' if keep_alive else 'close'

            # Handle the request - Function goes to handle_request()
            response = handle_request(method, path, version, headers, connection_mode)
            if isinstance(response, bytes):
                client_connection.sendall(response)
            else:
                client_connection.sendall(response.encode())

            if not keep_alive:
                break
    except socket.timeout:
        log_console(f"Connection timeout for {client_address}; Closing connection for keep-alive.")
    except Exception as e:
        warn_console(f"Error handling client {client_address}: {e}")
    finally:
        # Close the connection
        client_connection.close()

def main(): # Main part of the server
    try:
        # Create Socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        log_console(f"Listening on {SERVER_HOST}:{SERVER_PORT}...", always_print=True)
        server_socket.listen(QUEUE_TCP_CONNECTIONS)

        # Main loop to accept and handle incoming connections
        while True:
            client_connection, client_address = server_socket.accept()

            thread = threading.Thread(target=handle_client, args=(client_connection, client_address))
            thread.start()


    except KeyboardInterrupt:
        log_console("Terminating Web Server because of Keyboard Interrupt.")
    except Exception as e:
        warn_console(f"An error occurred: {e}")
    finally:
        server_socket.close()
        log_console("Server has been stopped.")


if __name__ == "__main__":
    main()