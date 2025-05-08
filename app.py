from flask import Flask, render_template, request, jsonify
import socket
import ssl
import json
import uuid

app = Flask(__name__)

CERT_PATH = 'cert.pem'  # Caminho para o seu certificado
KEY_PATH = 'chave.pem'  # Caminho para a sua chave privada

def send_request_to_server(payload, server_host, server_port):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # Se não tiver CA

    with socket.create_connection((server_host, server_port)) as sock:
        with context.wrap_socket(sock, server_hostname=server_host) as ssock:
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
    server_host = None
    server_port = None
    if request.method == 'POST':
        # Pega os valores de IP, Porta, CPF e Nome
        server_host = request.form.get('server_host')
        server_port = int(request.form.get('server_port'))
        cpf = request.form.get('cpf')
        nome = request.form.get('nome')

        try:
            # Construção do payload conforme o formato esperado
            payload = {}
            if cpf:
                payload = {"tipo": "cpf", "valor": cpf, "request_id": str(uuid.uuid4())}
            elif nome:
                payload = {"tipo": "nome", "valor": nome, "request_id": str(uuid.uuid4())}

            if not payload:
                error = "Informe CPF ou nome."
            else:
                if not server_host or not server_port:
                    error = "Informe o IP e a porta do servidor."
                else:
                    result = send_request_to_server(payload, server_host, server_port)

                    # Verificando a resposta
                    if 'erro' in result:
                        error = result['erro']
                    else:
                        # Organizando os dados para exibição
                        result_data = {
                            "tempo": result.get("tempo", "N/A"),
                            "colunas": result.get("colunas", []),
                            "dados": result.get("dados", [])
                        }
                        result = result_data

        except Exception as e:
            error = f"Erro na requisição: {str(e)}"

    return render_template('index.html', result=result, error=error)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, ssl_context=(CERT_PATH, KEY_PATH))
