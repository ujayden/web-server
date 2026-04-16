import socket # Basic socket library for TCP/IP communication
import threading # For Multi-threaded Web Server
import os 

# CONFIGURATION
SERVER_HOST = '0.0.0.0'  # Listen IP -> 0.0.0.0: All
SERVER_PORT = 80         # Standard HTTP port
SERVER_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__)) # src/server.py
SERVER_ROOT_DIR = os.path.join(os.path.dirname(SERVER_SOURCE_DIR), 'test_files') # Go one level up, then test_files/
ROOT_TO_INDEX_HTML = True # True: For "/" request -> "index.html", False: For "/" request -> 404
LOG_LEVEL = 2            # 0: No logs, 1: Basic logs, 2: Detailed logs
ACCESS_LOG_FILE = 'server.log'  # Records the historical information about the client requests and server responses

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

def generate_respond_headers(headers_dict):
    """
    Generate the HTTP response headers string from a dictionary of header key-value pairs.
    @param headers_dict: Header Dict
    @return: Formatted HTTP response headers string
    """
    return ''.join(f"{key}: {value}\r\n" for key, value in headers_dict.items())

def handle_request(method, path, version, request_headers):
    """
    Handle incoming HTTP request and craft appropriate HTTP response.
    @param method: HTTP method (ONLY GET, HEAD)
    @param path: Requested resource path
    @param version: HTTP version (e.g., HTTP/1.1)
    @param headers: Dictionary of HTTP headers
    @return: Formatted HTTP response, ready to be sent back to the client.
    """
    # TODO: Implement actual request handling logic here (e.g., serve files, handle errors, etc.)
    
    # First, we need to check if the method is supported (GET or HEAD)
    if method not in ['GET', 'HEAD']:
        warn_console(f"Unsupported HTTP method: {method}")
        response = generate_error_response(400)  # Bad Request for unsupported methods
        return response

    # Then, process path and try to serve the requested file
    if path == '/' and ROOT_TO_INDEX_HTML:
        file_path = os.path.join(SERVER_ROOT_DIR, 'index.html')
    elif path == '/' and not ROOT_TO_INDEX_HTML:
        warn_console(f"Root path '/' requested but ROOT_TO_INDEX_HTML is set to False.")
        response = generate_error_response(404, method)
        return response
    else:
        file_path = os.path.join(SERVER_ROOT_DIR, path.lstrip('/'))
 
    success, content = read_file(file_path)
    # Since no 500, success = False is treated as 404
    if not success:
        warn_console(f"File not found or IO error: {file_path}")
        response = generate_error_response(404, method)  # File Not Found
        return response

    # Identify the content type based on file extension
    content_type = generate_content_type(file_path)
    # Craft the HEADER of the response
    response_headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(content)) # For "Proper response message exchange" and avoid long loading time, 
    }
    # since read mode is rb, content = bytes, len(content) = byte size of the file, which = correct value for Content-Length header.

    first_line = f"HTTP/1.1 200 OK\r\n"
    header_part = generate_respond_headers(response_headers)
    # IF method is HEAD, we only return the header without the body
    response = first_line + header_part + "\r\n"
    if method == 'GET':
        response = response.encode() + content
    return response

def generate_error_response(status_code, method='GET'):
    """
    Generate general HTTP error response based on the status code provided. If the status code is not recognized, defaults is "Unknown Error".
    @param status_code: HTTP status code (e.g., 400, 403, 404)
    @param method: HTTP method (default: 'GET'), used to determine if the response should include a body (False for HEAD requests - RFC 9110)
    @return: Formatted HTTP response string with the appropriate status message and content.
    """
    status_message = STATUS_MESSAGES.get(status_code, "Unknown Error")
    body = status_message

    response_headers = {
        "Content-Type": "text/plain",
        "Content-Length": str(len(body))
    }

    first_line = f"HTTP/1.1 {status_code} {status_message}\r\n"
    header_part = generate_respond_headers(response_headers)
    response = first_line + header_part + "\r\n"

    if method != 'HEAD':
        response = response + body

    return response

def handle_client(client_connection, client_address):
    try:
        # Get the client request
        request = client_connection.recv(1024).decode()
        # Phrase HTTP request
        request_info = request.splitlines()
        # 1st line of HTTP request contains method, path and version
        if len(request_info) > 0:
            try:
                method, path, version = request_info[0].split()
            except ValueError:
                warn_console(f"Received malformed request from {client_address} - Invalid request line")
                response = generate_error_response(400)
                client_connection.sendall(response.encode())
                return
        else:
            warn_console(f"Received malformed request from {client_address} - No request lines")
            response = generate_error_response(400)
            client_connection.sendall(response.encode())
            return
        
        # Make rest of info of the request into a dictionary
        headers = {}
        for line in request_info[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key] = value

        # Handle the request - Function goest to handle_request()
        response = handle_request(method, path, version, headers)
        if isinstance(response, bytes): # GET method with binary content have encoded. Do not double encode.
            client_connection.sendall(response)
        else:
            client_connection.sendall(response.encode())
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
        #listen(No. of connections to queue)
        server_socket.listen(5)

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