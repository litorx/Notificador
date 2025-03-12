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

# 1) Instalar Dependências
pip install -r requirements.txt

# 2) Definir Variáveis de Ambiente
- export DATABASE_URL="postgresql://usuario:senha@host:porta/db"
- export TWILIO_ACCOUNT_SID="..."
- export TWILIO_AUTH_TOKEN="..."
- export TWILIO_FROM_NUMBER="whatsapp:+XXXX"
- export COMPANY_NAME="Folks"
- export PLATFORM_LINK="Plataforma"
- export USE_SANDBOX="true/false"

# 3) Executar
- **python notificador.py**
- **O script rodará em loop infinito, processando e enviando notificações.**

# 4) Implantar na Nuvem (opcional)
- **Dockerizar o script e enviar para GCP (Cloud Run) ou outro provedor.**
- **Ajustar variáveis de ambiente no serviço de destino.**

# Arquitetura Simplificada

```mermaid
flowchart TB
    subgraph BD["Banco de Dados (Cliente)"]
        A1["Tabelas: dados_estruturados dados_nao_estruturados"]
    end

    subgraph API_GET["API do Cliente (GET)"]
        B1["Recebe Dados de Exames"]
    end

    subgraph PROC["Processamento"]
        C1["Normalização de Texto"]
        C2["Classificação de Exames (TUSS + Regex)"]
        C3["Agrupamento por Paciente"]
        C4["Envio de Mensagens"]
    end

    subgraph ML["Modelo de ML (Opcional)"]
        G1["Classificador Avançado"]
    end

    subgraph MSG["(Twilio)"]
        D1["WhatsApp/SMS"]
    end

    subgraph APPS["Integrações Externas"]
        E1["Plataforma de Agendamento"]
    end

    subgraph API_POST["API do Cliente (POST)"]
        H1["Atualização de Registros"]
    end

    subgraph DATA["Visualização de Dados"]
        F1["Dashboards / Relatórios"]
    end

    %% Conexões Principais
    BD -->|Consulta| API_GET
    API_GET -->|Envia Dados| PROC
    PROC -->|Opcional Modelo ML| ML
    PROC -->|Envia Mensagens| MSG
    MSG -->|WhatsApp| APPS
    APPS -->|Agendamento Feito| API_POST
    API_POST -->|Atualiza DB| BD
    BD -->|Exibe Dados| DATA
```

##  Explicação dos Componentes

###  Banco de Dados (Cliente)
Contém registros de exames estruturados e não estruturados.

###  API do Cliente (GET)
- Consulta os dados do banco de dados do cliente.  
- Retorna exames pendentes e dados dos pacientes.

###  Processamento
- **Classificação de Exames** → Verifica se é imagem ou não (TUSS + Regex).  
- **Normalização de Texto** → Corrige erros e variações de escrita.  
- **Identificação TUSS** → Mapeia exames ao código correto.  
- **Envio de Notificação** → Prepara mensagens personalizadas.  

###  Serviço de Mensageria (Twilio)
- Envia mensagens via **WhatsApp**.  

###  Integrações Externas (Apps Terceiros)
- Redireciona o paciente para a **plataforma de agendamento** do cliente.  

###  Visualização de Dados (Data View)
- Painéis para monitoramento de envios, conversões e pendências.  

###  Machine Learning (Futuro)
- Modelo avançado para substituir Regex na classificação de exames.  

###  API do Cliente (POST)
- Atualiza o status dos registros após a notificação ser enviada.  


- **Banco de dados**: Registros estruturados e não estruturados.  
- **Script Notificador**: Lê dados em chunks, classifica e envia mensagens.  
- **Twilio**: Serviço de mensageria via WhatsApp.  
- **Plataforma de Agendamento**: Link para o paciente marcar o exame.  

# Melhorias Futuras
**Machine Learning Avançado**
- Substituir regex por um classificador robusto (Hugging Face, scikit etc.) para extrair tipo de exame e parte do corpo.

**Canal Bidirecional**
- Permitir respostas do paciente via WhatsApp, integrando com o agendamento automático.

**Testes A/B**
- Experimentar diferentes cópias de mensagem para maximizar conversão.

**Dashboards**
- Construir relatórios com Plotly ou Looker Studio, exibindo taxa de conversão, exames pendentes e enviados.
