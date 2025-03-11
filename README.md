# Notificador

Script em Python **plug-and-play**, com foco em **escalabilidade**, **baixo custo** e **alto rendimento**.  
Seu principal objetivo é **monitorar** o banco de dados de clientes, **identificar exames de imagem pendentes** e **enviar mensagens** via WhatsApp para lembrar os pacientes de agendar esses exames.

---

## Visão Geral

- **Leitura em Lotes (Chunks)**  
  Lida com grandes volumes (milhares/milhões de registros) sem sobrecarregar a memória.

- **Classificação de Exames**  
  - Para dados **estruturados** (com `cd_tuss`), faz mapeamento imediato a partir de um dicionário TUSS.  
  - Para dados **não estruturados**, normaliza o texto (remoção de acentos, termos irrelevantes) e aplica **regex** para identificar exames de imagem.

- **Envio de Mensagens**  
  - Integração com **Twilio** para envio via **WhatsApp**.  
  - Mensagem amigável, incluindo o nome do usuário, texto persuasivo e link para plataforma de agendamento.

- **Evita Repetição**  
  - Marca registros como `notified=true` para que o mesmo paciente não receba mensagens duplicadas.

- **Persistência**  
  - Usa **PostgreSQL** (pode ser adaptado a outros bancos).  
  - Conexão gerenciada via **SQLAlchemy**.

- **Cloud**  
  - Fácil de implantar em **GCP** (Cloud Run, Cloud Functions) ou outros provedores, podendo rodar em loop infinito.

---

## Tecnologias Principais

- **Python**  
  Produtivo, robusto e com ampla comunidade.

- **SQLAlchemy**  
  - ORM que abstrai a comunicação com bancos relacionais.  
  - Facilita operações complexas de forma mais simples.

- **nltk**  
  - Biblioteca leve para tarefas de NLP básicas.  
  - Útil para normalizar e tokenizar textos rapidamente.

- **pandas**  
  - DataFrames para manipulação eficiente de dados.  
  - Suporte a processamento em chunks, evitando sobrecarga de memória.

- **Twilio**  
  - Plataforma confiável para envio de mensagens WhatsApp/SMS.  
  - Possui modo sandbox para testes e modo produção.

- **Plotly** (opcional)  
  - Geração de dashboards e visualizações interativas.  
  - Pode ser usado para monitorar taxa de conversão e estatísticas de envio.

- **GCP** (opcional)  
  - Desempenho e escalabilidade automática via Cloud Run.  
  - Cotas gratuitas que permitem iniciar o projeto com custo quase zero.

- **PostgreSQL**  
  - Banco de dados seguro e escalável.  
  - Altamente compatível com Python/SQLAlchemy.

---

## Fluxo de Trabalho

1. **Banco de Dados**:  
   - Tabelas `dados_estruturados` (com `cd_tuss`) e `dados_nao_estruturados` (texto livre).  
   - Campo `notified` para controlar se o registro já foi notificado.

2. **Leitura em Lotes**:  
   - A cada iteração, o script lê até `chunk_size` registros pendentes (`notified=false`) de cada tabela.

3. **Classificação**:  
   - Se houver `cd_tuss`, mapeia para um exame (ex.: “Tomografia Computadorizada”).  
   - Caso contrário, normaliza a string e aplica regex para identificar se é exame de imagem.

4. **Agrupamento por Paciente**:  
   - Reúne todos os exames pendentes daquele telefone (ex.: “Ressonância Magnética”, “Mamografia”).  
   - Gera **uma única mensagem** contendo todos os exames.

5. **Envio de Mensagens**:  
   - Usa **Twilio** para envio via WhatsApp (prefixo “whatsapp:+55”).  
   - Mensagem amigável, citando nome do paciente e link de agendamento (`PLATFORM_LINK`).

6. **Marcação de Notificados**:  
   - Após envio, marca todos os registros daquele telefone como `notified=true`, evitando reenvio.

7. **Loop Infinito**:  
   - O script dorme alguns segundos (`sleep_seconds`) e volta a ler o próximo lote.

---

## Como Executar

bash
# 1) Instalar Dependências
pip install -r requirements.txt

# 2) Definir Variáveis de Ambiente
export DATABASE_URL="postgresql://usuario:senha@host:porta/db"
export TWILIO_ACCOUNT_SID="..."
export TWILIO_AUTH_TOKEN="..."
export TWILIO_FROM_NUMBER="whatsapp:+14155238886"
export COMPANY_NAME="Folks"
export PLATFORM_LINK="https://calendly.com/"
export USE_SANDBOX="true"

# 3) Executar
python notificador.py
# O script rodará em loop infinito, processando e enviando notificações.

# 4) Implantar na Nuvem (opcional)
# Dockerizar o script e enviar para GCP (Cloud Run) ou outro provedor.
# Ajustar variáveis de ambiente no serviço de destino.

# Arquitetura Simplificada

mermaid
flowchart LR
    A((Banco de dados)) --> B[Script Notificador]
    B --> C[Classificação de Exames<br/>(TUSS + Regex)]
    C --> D((Twilio/WhatsApp))
    B --> E[Marcar Registros Notificados]
    D --> F(Plataforma de Agendamento)


**Banco de dados**: Registros estruturados e não estruturados.  
**Script Notificador**: Lê dados em chunks, classifica e envia mensagens.  
**Twilio**: Serviço de mensageria via WhatsApp.  
**Plataforma de Agendamento**: Link para o paciente marcar o exame.  

## Melhorias Futuras

### Machine Learning Avançado
Substituir regex por um classificador robusto (Hugging Face, scikit etc.) para extrair tipo de exame e parte do corpo.

### Canal Bidirecional
Permitir respostas do paciente via WhatsApp, integrando com o agendamento automático.

### Testes A/B
Experimentar diferentes cópias de mensagem para maximizar conversão.

### Dashboards
Construir relatórios com Plotly ou Looker Studio, exibindo taxa de conversão, exames pendentes e enviados.
