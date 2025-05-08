from flask import Flask, render_template, request, jsonify
import socket
import ssl
import json

app = Flask(__name__)

SERVER_HOST = 'localhost'
SERVER_PORT = 12345
CERT_PATH = 'cert.pem'  # Caminho para o certificado do seu servidor

def send_request_to_server(payload):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # Se não tiver CA

    with socket.create_connection((SERVER_HOST, SERVER_PORT)) as sock:
        with context.wrap_socket(sock, server_hostname=SERVER_HOST) as ssock:
            request_data = json.dumps(payload).encode('utf-8')
            header = len(request_data).to_bytes(4, 'big')
            ssock.sendall(header + request_data)

            header = ssock.recv(4)
            length = int.from_bytes(header, 'big')
            response_data = b""
            while len(response_data) < length:
                chunk = ssock.recv(length - len(response_data))
                if not chunk:
                    break
                response_data += chunk

            return json.loads(response_data.decode('utf-8'))

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    error = None
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        nome = request.form.get('nome')

        try:
            payload = {}
            if cpf:
                payload['cpf'] = cpf
            elif nome:
                payload['nome'] = nome

            if not payload:
                error = "Informe CPF ou nome."
            else:
                result = send_request_to_server(payload)

        except Exception as e:
            error = f"Erro na requisição: {str(e)}"

    return render_template('index.html', result=result, error=error)

if __name__ == '__main__':
    app.run(debug=True, port=5000,ssl_context=('cert.pem', 'chave.pem'))
