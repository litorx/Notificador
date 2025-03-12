"""
Notificador (Produção) - Versão Final
"""

import os
import re
import time
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from twilio.rest import Client

# Tente remover acentos estranhos ("Ressonfncia" => "Ressonancia")
try:
    from unidecode import unidecode
    HAS_UNIDECODE = True
except ImportError:
    HAS_UNIDECODE = False


# Configurações de Logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("folks_notifier")


# Variáveis de Ambiente

DATABASE_URL = os.getenv("DATABASE_URL")  
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")  
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")    
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")  
COMPANY_NAME = os.getenv("COMPANY_NAME")
PLATFORM_LINK = os.getenv("PLATFORM_LINK")
USE_SANDBOX = os.getenv("USE_SANDBOX", "true").lower() == "true"


# Conexão com o Banco de Dados

engine = create_engine(DATABASE_URL)


# Dicionário TUSS, com (nome_exame, "imagem"/"nao_imagem") serapandos os exames para uso futuro.

TUSS_EXAMS = {
    40901114: ("Ultrassonografia", "imagem"),
    40501012: ("Tomografia Computadorizada", "imagem"),
    40601110: ("Ressonância Magnética", "imagem"),
    40901113: ("Mamografia", "imagem"),
    40801013: ("Radiografia", "imagem"),
    40101015: ("Colonoscopia", "nao_imagem"),
    40701121: ("Endoscopia", "nao_imagem"),
}


# Regex para texto não estruturado: (regex, exame_final, ex_type)
# Adicionei variações de "ressonnancia", "ressonfncia" etc. para unificar

EXAM_PATTERNS = [
    (r'(ressonancia|ressonnancia|ressonância|rm|ressonfncia)', "Ressonância Magnética", "imagem"),
    (r'(tomografia|tc)',                                       "Tomografia Computadorizada", "imagem"),
    (r'(ultrassom|ultrassonografia)',                          "Ultrassonografia", "imagem"),
    (r'(radiografia|raio\-x|raiox)',                           "Radiografia", "imagem"),
    (r'(mamografia|mamas)',                                    "Mamografia", "imagem"),
    (r'colonoscop',                                            "Colonoscopia", "nao_imagem"),
    (r'endoscop',                                              "Endoscopia", "nao_imagem"),
]

# Termos que indicam "sem exame" ou "checkup" para evitar menssagens sem sentido.
IGNORE_TERMS = {
    "sem exame", "exame não especificado", "apenas checkup",
    "sem exame adicional", "checkup geral", "apenas checkup geral"
}


# Função: normalizar texto (remove acentos, substitui "fncia" => "nancia" etc.)

def normalize_text(txt):
    """
    Normaliza texto para facilitar o match:
    1) Converte para minúsculas
    2) Remove acentos (unidecode) se tiver.
    3) Substitui 'fncia' => 'nancia' (ex.: 'ressonfncia' => 'ressonancia') por conta dos acentos
    4) Remove termos como 'adicional', 'recomendada', 'programada', 'do', 'da', 'de'
    5) Remove múltiplos espaços
    """
    if not txt:
        return ""
    txt_lower = txt.lower()
    if HAS_UNIDECODE:
        txt_lower = unidecode(txt_lower)
    # Corrige 'fncia' => 'nancia'
    txt_lower = re.sub(r'fncia', 'nancia', txt_lower)
    # Remove palavras irrelevantes
    txt_lower = re.sub(r'\b(adicional|recomendada|programada|do|da|de)\b', '', txt_lower)
    # Remove múltiplos espaços
    txt_lower = re.sub(r'\s+', ' ', txt_lower).strip()
    return txt_lower


# Função: classificar exame (cd_tuss ou regex)

def classify_exam(cd_tuss, ds_receita):
    """
    1) Se cd_tuss estiver em TUSS_EXAMS => (exame, ex_type)
    2) Caso contrário => normaliza ds_receita, casa com EXAM_PATTERNS
    3) Se nada encontrado => "Sem Exame"
    """
    if cd_tuss and cd_tuss in TUSS_EXAMS:
        return TUSS_EXAMS[cd_tuss]  # (exame, ex_type)

    norm = normalize_text(ds_receita)
    if not norm or norm in IGNORE_TERMS:
        return ("Sem Exame", "nao_imagem")

    for (rgx, exame_final, ex_type) in EXAM_PATTERNS:
        if re.search(rgx, norm, re.IGNORECASE):
            return (exame_final, ex_type)

    # Se não encontrou nada, retorna o texto normalizado (title) como fallback
    return (norm.title(), "nao_imagem")


# Função: gerar mensagem bullet (sem pronomes), ignorando "Sem Exame" e coisas do tipo.

def build_message_for_exams(client_name, exam_list):
    """
    Recebe exam_list = [(exame, ex_type), ...].
    Deduplica, remove "Sem Exame" e IGNORE_TERMS, exibe em bullets.
    Exemplo de saída:

    Olá Rodrigo,

    Identificamos que você tem alguns exames pendentes:

    • Ressonância Magnética
    • Tomografia Computadorizada

    É fundamental agendar...
    """
    unique_img = set()
    unique_nonimg = set()

    for (exame, ex_type) in exam_list:
        ex_lower = exame.lower()
        if ex_lower in IGNORE_TERMS or ex_lower.startswith("sem exame"):
            continue
        if ex_type == "imagem":
            unique_img.add(exame)
        else:
            unique_nonimg.add(exame)

    # Ordena
    img_list = sorted(unique_img)
    nonimg_list = sorted(unique_nonimg)

    lines = []
    lines.append(f"Olá {client_name},")
    lines.append("")
    lines.append("Identificamos que você tem alguns exames pendentes:")
    lines.append("")

    bullet_lines = []
    for item in img_list:
        bullet_lines.append(f"• {item}")
    for item in nonimg_list:
        bullet_lines.append(f"• {item}")

    if bullet_lines:
        lines.extend(bullet_lines)
    else:
        lines.append("• Nenhum exame específico identificado.")

    lines.append("")
    lines.append("É fundamental agendar o quanto antes para garantir sua saúde em dia.")
    lines.append(f"Agende facilmente pelo link: {PLATFORM_LINK}")
    lines.append("")
    lines.append(f"Caso precise de suporte, a equipe {COMPANY_NAME} está aqui para ajudar.")
    lines.append("")
    lines.append("Um abraço,")
    lines.append(f"Equipe {COMPANY_NAME}")

    return "\n".join(lines)


# Função: enviar notificação via Twilio

def send_notification(to_number, client_name, exam_list):
    """
    - Monta a mensagem bullet.
    - Envia via Twilio (Sandbox ou Produção).
    - Trata erro 63038 (erro mais comum de limite diario).
    """
    # Ajusta número para WhatsApp se não tiver prefixo
    if not to_number.startswith("whatsapp:"):
        to_number = "whatsapp:+55" + to_number

    msg_body = build_message_for_exams(client_name, exam_list)

    # Se mockado
    if TWILIO_ACCOUNT_SID == "TWILIO_ACCOUNT_SID":
        logger.info(f"(Simulação) Mensagem para {client_name} ({to_number}):\n{msg_body}")
        return True

    from_number = "whatsapp:+14155238886" if USE_SANDBOX else TWILIO_FROM_NUMBER
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    try:
        message = twilio_client.messages.create(
            from_=from_number,
            body=msg_body,
            to=to_number
        )
        logger.info(f"Mensagem enviada para {client_name} ({to_number}). SID={message.sid}")
        return True
    except Exception as e:
        err_str = str(e)
        if "63038" in err_str:
            logger.warning(f"Limite diário atingido para {client_name} ({to_number}).")
            return False
        else:
            logger.error(f"Erro ao enviar p/ {client_name} ({to_number}): {e}")
            return False


# Função: marcar todos do telefone como notified=true

def mark_as_notified_by_tel(conn, tel):
    """
    Marca todos os registros (notified=false) para esse tel (telefone)
    em dados_estruturados e dados_nao_estruturados => notified=true
    evitando duplicidade nos próximos chunks.
    """
    for tbl in ["dados_estruturados", "dados_nao_estruturados"]:
        conn.execute(
            text(f"UPDATE public.{tbl} SET notified=true WHERE tel=:tel AND NOT notified"),
            {"tel": tel}
        )
        conn.commit()


# Função principal: loop infinito com leitura chunk-based

def infinite_loop(chunk_size=1000, sleep_seconds=30):
    """
    1) Lê 'chunk_size' registros pendentes de cada tabela (WHERE notified=false).
    2) Agrupa por telefone, classifica e deduplica exames.
    3) Envia 1 mensagem por telefone com todos exames pendentes, marca todos do tel => notified=true.
    4) Dorme e repete.

    :param chunk_size: quantos registros buscar por iteração em cada tabela
    :param sleep_seconds: quanto tempo dormir se não encontrar registros
    """
    while True:
        logger.info("Iniciando varredura de dados não notificados (Produção, chunk_size=%d).", chunk_size)
        any_sent = False

        # Abre conexão
        with engine.connect() as conn:
            # Lê chunk da tabela dados_estruturados
            df1 = pd.read_sql(
                text(
                    "SELECT id, solicitante, tel, ds_receita, cd_tuss "
                    "FROM public.dados_estruturados "
                    "WHERE NOT notified "
                    "ORDER BY id LIMIT :lim"
                ),
                conn,
                params={"lim": chunk_size}
            )

            # Lê chunk da tabela dados_nao_estruturados
            df2 = pd.read_sql(
                text(
                    "SELECT id, solicitante, tel, ds_receita "
                    "FROM public.dados_nao_estruturados "
                    "WHERE NOT notified "
                    "ORDER BY id LIMIT :lim"
                ),
                conn,
                params={"lim": chunk_size}
            )

            # Se ambos vazios => dorme e recomeça
            if df1.empty and df2.empty:
                logger.info("Nenhum registro pendente encontrado. Dormindo...")
                time.sleep(sleep_seconds)
                continue

            # Concatena
            df = pd.concat([df1, df2], ignore_index=True)

            # Agrupa por telefone
            grouped = {}
            for _, row in df.iterrows():
                cd_tuss = row.get("cd_tuss") 
                ds_receita = row.get("ds_receita", "")
                tel = row["tel"]
                solicitante = row["solicitante"]

                # Classifica
                exame, ex_type = classify_exam(cd_tuss, ds_receita)

                if tel not in grouped:
                    grouped[tel] = {
                        "client_name": solicitante,
                        "exams": []
                    }
                grouped[tel]["exams"].append((exame, ex_type))

            # Envia mensagem por telefone
            for tel, info in grouped.items():
                c_name = info["client_name"]
                exam_list = info["exams"]
                ok = send_notification(tel, c_name, exam_list)
                if ok:
                    any_sent = True
                    # Marca todos do tel => sem duplicidade
                    mark_as_notified_by_tel(conn, tel)

        # Se enviou algo => dorme 5s, senão => dorme sleep_seconds
        if any_sent:
            logger.info("Envios realizados neste ciclo. Retomando em 5s.")
            time.sleep(5)
        else:
            logger.info(f"Nenhum envio realizado neste ciclo. Dormindo {sleep_seconds}s.")
            time.sleep(sleep_seconds)


# main(): Inicia o loop infinito

def main():
    logger.info("Iniciando Envio de Notificações.")
    infinite_loop(chunk_size=1000, sleep_seconds=30)
    logger.info("Script finalizado.")


# Execução

if __name__ == "__main__":
    main()
