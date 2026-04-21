import socket # Basic socket library for TCP/IP communication
import threading # For Multi-threaded Web Server
import os 
from datetime import datetime, timezone
import logging

# CONFIGURATION
SERVER_HOST = '0.0.0.0'  # Listen IP -> 0.0.0.0: All
SERVER_PORT = 80         # Standard HTTP port
SERVER_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__)) # src/server.py
SERVER_ROOT_DIR = os.path.join(os.path.dirname(SERVER_SOURCE_DIR), 'test_files') # Go one level up, then test_files/
ROOT_TO_INDEX_HTML = True # True: For "/" request -> "index.html", False: For "/" request -> 404
LOG_LEVEL = 2            # 0: No logs, 1: Basic logs, 2: Detailed logs
ACCESS_LOG_FILE = 'server.log'  # Records the historical information about the client requests and server responses
ACCESS_LOG_LOCATION = os.path.join(os.path.dirname(SERVER_SOURCE_DIR), ACCESS_LOG_FILE)  # Log file in the same directory as server.py
ACCESS_LOG_TO_CONSOLE = True # Print access log to console or not.
KEEP_ALIVE_TIMEOUT_SECONDS = 5  # Timeout for idle persistent connections
QUEUE_TCP_CONNECTIONS = 256 # Number of TCP connections to queue (for listen())

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

BLOCK_PATH_LIST = {
    # For demostrate 403 Forbidden
    # These PATH will generate 403
    '/forbidden.html', # Specific PATH
}
# END OF CONFIGURATION


# LOGGING FUNCTIONS
def log_console(message, always_print=False):
    if LOG_LEVEL >= 2 or always_print:
        print(f"[LOG] {message}")

def warn_console(message):
    if LOG_LEVEL >= 1:
        print(f"[WARN] {message}")

logger = logging.getLogger("access_logger")
if not logger.handlers:
    file_handler = logging.FileHandler(ACCESS_LOG_LOCATION)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

def access_logger(client_address, method, path, version, status_code, content_length, connection_mode, request_headers=None):
    """
    Log access info for each HTTP request.

    @param client_address: Client IP address and port tuple from socket.accept()
    @param method: HTTP method from request line
    @param path: Request path
    @param version: HTTP version from request line
    @param status_code: HTTP status code returned to client
    @param content_length: Content-Length returned to client
    @param connection_mode: 'keep-alive' or 'close'
    @param request_headers: Request header dictionary (used for User-Agent)
    """
    client_ip, client_port = client_address
    user_agent = "-"
    if request_headers:
        user_agent = request_headers.get('user-agent', '-') or '-'

    user_agent = str(user_agent).replace('\\', '\\\\').replace('"', '\\"')

    timestamp = datetime.now().astimezone().strftime("%d/%b/%Y:%H:%M:%S %z")
    request_line = f"{method} {path} {version}"
    log_line = (
        f"{client_ip} - {client_port} [{timestamp}] \"{request_line}\" "
        f"{status_code} {content_length} \"{connection_mode}\" \"{user_agent}\""
    )

    if ACCESS_LOG_TO_CONSOLE:
        log_console(log_line)

    try:
        logger.info(log_line)
    except Exception as e:
        warn_console(f"Failed to write access log entry: {e}")

def extract_response_log_fields(response_bytes):
    """
    Extract status code and content length from raw HTTP response bytes.
    @param response_bytes: Full HTTP response as bytes
    @return: Tuple (status_code, content_length)
    """
    status_code = 0
    content_length = 0

    try:
        header_part = response_bytes.split(b'\r\n\r\n', 1)[0]
        header_text = header_part.decode('iso-8859-1')
        header_lines = header_text.split('\r\n')

        first_line_parts = header_lines[0].split()
        if len(first_line_parts) >= 2:
            status_code = int(first_line_parts[1])

        for line in header_lines[1:]:
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            if key.strip().lower() == 'content-length':
                content_length = int(value.strip())
                break
    except Exception:
        pass

    return status_code, content_length

# END OF LOGGING FUNCTIONS

# FILE IO FUNCTIONS
def read_file(file_path):
    """
    Read file (Binary Mode) from specific path, the return is the content of the file and do not modified. 
    [!] FileNotFoundError does not print in console. Since we dont have 500, it will assume **404** in future step.
    @param file_path: The path of the file to be read.
    @return: Tuple (success, content, error_types) - success: boolean indicating read status,  content: file content if successful, or None if not, error_types: string indicating the type of error if unsuccessful.
    
    """
    try:
        file_path = os.path.abspath(file_path)

        # Safety check
        if os.path.commonpath([SERVER_ROOT_DIR, file_path]) != SERVER_ROOT_DIR:
            raise PermissionError("Attempt to access file outside of server root directory.")

        # Convert filesystem path back to URL-like path for BLOCK_PATH_LIST matching.
        normalized_path = '/' + os.path.relpath(file_path, SERVER_ROOT_DIR).replace('\\', '/')
        if normalized_path in BLOCK_PATH_LIST:
            raise PermissionError(f"Blocked path from BLOCK_PATH_LIST: {normalized_path}")

        with open(file_path, 'rb') as file:
            return True, file.read(), None
    except PermissionError as e:
        # This include: OS-level permission issues, illegal path, and BLOCK_PATH_LIST check
        warn_console(f"Permission denied for file {file_path}: {e}")
        return False, None, "permission_denied"
    except FileNotFoundError:
        return False, None, "not_found"
    except Exception as e:
        warn_console(f"Error reading file {file_path}: {e}")
        return False, None, "internal_error"

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

def http_version_checker(version):
    """
    Validate HTTP version from request line.
    @param version: HTTP version string from request line
    @return: True if version is supported, otherwise False
    """
    return version in ['HTTP/1.0', 'HTTP/1.1']

def host_header_checker(version, request_headers):
    """
    Validate Host header for HTTP/1.1 requests.
    @param version: HTTP version string from request line
    @param request_headers: Request header dictionary
    @return: True if Host header is valid (or not required), otherwise False
    """
    if version != 'HTTP/1.1':
        return True
    return bool(request_headers.get('host', '').strip())

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
 
    success, content, error_type = read_file(file_path)
    if not success:
        if error_type == "permission_denied":
            warn_console(f"Forbidden file access: {file_path}")
            response = generate_error_response(403, method, connection_mode)
        else:
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

def handle_client(client_connection, client_address, request_buffer=b''):
    close_connection = True
    try:
        client_connection.settimeout(KEEP_ALIVE_TIMEOUT_SECONDS)

        raw_request, request_buffer = read_raw_http_request(client_connection, request_buffer)
        if raw_request is None:
            return

        method, path, version, headers = parse_http_request(raw_request)
        if method is None:
            warn_console(f"Received malformed request from {client_address} - Invalid request line")
            response = generate_error_response(400, connection_mode='close')
            response_bytes = response.encode()
            client_connection.sendall(response_bytes)
            status_code, content_length = extract_response_log_fields(response_bytes)
            access_logger(client_address, 'UNKNOWN', '-', 'HTTP/1.1', status_code, content_length, 'close', {})
            return

        if not http_version_checker(version):
            warn_console(f"Unsupported HTTP version from {client_address}: {version}")
            response = generate_error_response(400, connection_mode='close')
            response_bytes = response.encode()
            client_connection.sendall(response_bytes)
            status_code, content_length = extract_response_log_fields(response_bytes)
            access_logger(client_address, method, path, version, status_code, content_length, 'close', headers)
            return

        if not host_header_checker(version, headers):
            warn_console(f"Missing Host header in HTTP/1.1 request from {client_address}")
            response = generate_error_response(400, connection_mode='close')
            response_bytes = response.encode()
            client_connection.sendall(response_bytes)
            status_code, content_length = extract_response_log_fields(response_bytes)
            access_logger(client_address, method, path, version, status_code, content_length, 'close', headers)
            return

        # Early check if the method is supported
        is_supported_method = method in ['GET', 'HEAD']
        keep_alive = keep_alive_checker(version, headers) and is_supported_method
        connection_mode = 'keep-alive' if keep_alive else 'close'

        # Handle the request - Function goes to handle_request()
        response = handle_request(method, path, version, headers, connection_mode)
        if isinstance(response, bytes):
            response_bytes = response
        else:
            response_bytes = response.encode()

        client_connection.sendall(response_bytes)
        status_code, content_length = extract_response_log_fields(response_bytes)
        access_logger(client_address, method, path, version, status_code, content_length, connection_mode, headers)

        if keep_alive:
            # One thread handles one request; keep-alive hands the same socket to a new thread for the next request.
            next_thread = threading.Thread(target=handle_client, args=(client_connection, client_address, request_buffer))
            next_thread.start()
            close_connection = False
    except socket.timeout:
        log_console(f"Connection timeout for {client_address}; Closing connection for keep-alive.")
    except Exception as e:
        warn_console(f"Error handling client {client_address}: {e}")
    finally:
        # Close the connection if there is no keep-alive thread handoff
        if close_connection:
            client_connection.close()

def main(): # Main part of the server
    server_socket = None
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
        if server_socket:
            server_socket.close()
        log_console("Server has been stopped.")


if __name__ == "__main__":
    main()