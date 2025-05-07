import socket
import subprocess
import os

def get_ipv4_address():
    """Captura o IP da máquina atual"""
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

def generate_ssl_key():
    """Gera a chave SSL sem usar o arquivo .conf"""
    try:
        ipv4_address = get_ipv4_address()
        print(f"IPv4 da máquina: {ipv4_address}")
        
        # Configurações diretamente no comando OpenSSL
        subject = f"/CN={ipv4_address}/O=Unipampa/C=BR"
        
        # Gerar chave privada e pública com OpenSSL sem usar o arquivo .conf
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:4096', '-nodes', 
                        '-keyout', 'chave.pem', '-out', 'cert.pem', '-days', '365', 
                        '-subj', subject], check=True)
        print("Chave privada e pública geradas com sucesso!")
    except subprocess.CalledProcessError as e:
        print(f"Erro ao gerar chave SSL: {e}")

def main():
    # Gerar a chave SSL sem o arquivo .conf
    generate_ssl_key()

if __name__ == "__main__":
    main()
