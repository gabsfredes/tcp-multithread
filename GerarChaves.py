import socket
import subprocess
import os

def get_ipv4_address():
    """Captura o IP da máquina atual"""
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

def modify_openssl_config(ipv4):
    """Modifica o arquivo openssl.cnf com o IPv4 da máquina"""
    config_file_path = 'openssl.cnf'  # Caminho para o arquivo openssl.cnf
    with open(config_file_path, 'r') as file:
        config_content = file.read()

    # Substituindo o IP no campo CN e IP.1 (seções relevantes do arquivo)
    config_content = config_content.replace('CN = 26.83.32.20', f'CN = {ipv4}')
    config_content = config_content.replace('IP.1 = 26.83.32.20', f'IP.1 = {ipv4}')
    
    with open(config_file_path, 'w') as file:
        file.write(config_content)

def generate_ssl_key():
    """Gera a chave SSL utilizando o OpenSSL com a configuração modificada"""
    try:
        # Gerar chave privada e pública com OpenSSL (ajuste conforme necessário)
        subprocess.run(['openssl', 'req', '-new', '-newkey', 'rsa:2048', '-nodes', 
                        '-keyout', 'chave.pem', '-out', 'cert.pem', 
                        '-config', 'openssl.cnf'], check=True)
        print("Chave privada e pública geradas com sucesso!")
    except subprocess.CalledProcessError as e:
        print(f"Erro ao gerar chave SSL: {e}")

def main():
    ipv4_address = get_ipv4_address()
    print(f"IPv4 da máquina: {ipv4_address}")
    
    # Modificar a configuração do OpenSSL com o IP da máquina
    modify_openssl_config(ipv4_address)
    
    # Gerar a chave SSL
    generate_ssl_key()

if __name__ == "__main__":
    main()
