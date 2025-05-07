# Projeto Cliente-Servidor Multi-thread

Este projeto, desenvolvido para disciplina de Redes de Computadores do curso de Engenharia de Computação da UNIPAMPA campus bagé, implementa um sistema cliente-servidor com múltiplas threads, utilizando Python, PyQt5 e SSL para comunicação segura. O servidor recebe consultas sobre CPF e nome de clientes a partir do cliente, utilizando um banco de dados SQLite.

## Requisitos

Para rodar o projeto, é necessário ter os seguintes requisitos instalados:

- Python 3.8 ou superior
- PyQt5
- SQLite (banco de dados)
- Certificado SSL (cert.pem e chave.pem)
- Bibliotecas de terceiros: `ssl`, `socket`, `threading`, `json`, `uuid`

Você pode instalar as dependências necessárias com _pip_

Após a instalação dos pacotes necessários, clone o repositório para sua máquina
```bash
git clone https://github.com/gabsfredes/tcp-multithread/
```

## Certificados SSL

A geração do certificado SSL deve ser feita antes de executar o projeto pela primeira vez. As instruções de como gerar o certificado estão no arquivo [Gerar Chave.txt]. Você terá duas chaves geradas:

- **Chave privada**: `chave.pem`
- **Chave pública**: `cert.pem`

A chave **privada** (`chave.pem`) deve ser mantida no servidor e não deve ser compartilhada. A chave **pública** (`cert.pem`) é a que será compartilhada com quem irá executar o cliente, ou pode ser mantida na mesma máquina caso você esteja executando tanto o servidor quanto o cliente localmente.

Siga as instruções no arquivo [Gerar Chave.txt] para gerar e configurar os certificados antes de rodar o programa.

### Estrutura do Banco de Dados

O banco de dados utilizado neste projeto possui a seguinte estrutura:

1. **Tabela `cpf`**
   - **cpf** (VARCHAR): CPF do cliente.
   - **nome** (VARCHAR): Nome do cliente.
   - **sexo** (CHAR): Sexo do cliente.
   - **nasc** (DATE): Data de nascimento do cliente.
   
   A tabela `cpf` é **indexada** para garantir uma pesquisa mais rápida, especialmente nas consultas baseadas no campo `cpf`. O índice na tabela `cpf` foi criado para otimizar as buscas realizadas nas colunas `cpf` e `nome`, melhorando a performance em consultas, especialmente quando o banco de dados contém um grande número de registros.

## Executando o projeto
Caso você irá testar usando a mesmq máquina, execute ambos arquivos principais no seu computador com os comandos `python servidor.py` e `python cliente.py`. As informações solicitadas pelo servidor são à seu gosto e de acordo com o poder de processamento da sua máquina. O IP **DEVE** ser o mesmo utilizado para gerar as chaves SSL (ou seja, o seu endereço IPv4), a porta fica à seu critério, recomendamos a porta `5000`.

Pronto, agora basta conectar no mesmo IP e Porta no cliente e realizar as buscas que você deseja no seu banco criado.
