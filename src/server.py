import socket # Basic socket library for TCP/IP communication
import threading # For Multi-threadedm Web Server
import os 

# CONFIGURATION
SERVER_HOST = '0.0.0.0'  # Listen IP -> 0.0.0.0: All
SERVER_PORT = 80         # Standard HTTP port
SERVER_ROOT_DIR = os.path.join(os.getcwd(), 'test_files')
LOG_LEVEL = 2            # 0: No logs, 1: Basic logs, 2: Detailed logs

# END OF CONFIGURATION

def log(message, always_print=False):
    if LOG_LEVEL >= 2 or always_print:
        print(f"[LOG] {message}")

def warn(message):
    if LOG_LEVEL >= 1:
        print(f"[WARN] {message}")

def handle_request(request):
    # TODO: Implement request parsing and response generation
    log(f"Received request: {request}")
    # Return a simple HTTP
    response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nHello, World!"
    return response

def handle_client(client_connection, client_address):
    try:
        # Get the client request
        request = client_connection.recv(1024).decode()
        # Handle the request
        response = handle_request(request)
        client_connection.sendall(response.encode())
    except Exception as e:
        warn(f"Error handling client {client_address}: {e}")
    finally:
        # Close the connection
        client_connection.close()

def main(): # Main part of the server
    try:
        # Create Socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        log(f"Listening on {SERVER_HOST}:{SERVER_PORT}...", always_print=True)
        #listen(No. of connections to queue)
        server_socket.listen(5)

        # Main loop to accept and handle incoming connections
        while True:
            client_connection, client_address = server_socket.accept()

            thread = threading.Thread(target=handle_client, args=(client_connection, client_address))
            thread.start()


    except KeyboardInterrupt:
        log("Terminating Web Server because of Keyboard Interrupt.")
    except Exception as e:
        warn(f"An error occurred: {e}")
    finally:
        server_socket.close()
        log("Server has been stopped.")


if __name__ == "__main__":
    main()