import socket
import os

def load_ruby_script(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), '..', 'ruby_scripts', f'{name}.rb')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def send_ruby_command(ruby_script: str) -> str:
    HOST = '127.0.0.1'
    PORT = 8080
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((HOST, PORT))
            
            clean_script = ruby_script.replace('\r', '')
            s.sendall(clean_script.encode('utf-8'))
            s.shutdown(socket.SHUT_WR)
            
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk: break
                response += chunk
            return response.decode('utf-8')
    except ConnectionRefusedError:
        return f"Error: Connection refused. Is SketchUp running and listening on {HOST}:{PORT}?"
    except socket.timeout:
        return "Error: Connection timed out after 5 seconds."
    except Exception as e:
        return f"Error: An unexpected network error occurred - {str(e)}"
