import os
import re
import time
import logging
import pandas as pd
import nltk
from sqlalchemy import create_engine, text
from datetime import datetime
from twilio.rest import Client


try:
    from unidecode import unidecode
    HAS_UNIDECODE = True
except ImportError:
    HAS_UNIDECODE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("folks_notifier")

DATABASE_URL = os.getenv("DATABASE_URL")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Folks")
PLATFORM_LINK = os.getenv("PLATFORM_LINK", "https://calendly.com/")
USE_SANDBOX = os.getenv("USE_SANDBOX")


nltk.download("punkt")


engine = create_engine(DATABASE_URL)


TUSS_EXAMS = {
    40901114: ("Ultrassonografia", "sua", "imagem"),
    40501012: ("Tomografia Computadorizada", "sua", "imagem"),
    40601110: ("Ressonância Magnética", "sua", "imagem"),
    40901113: ("Mamografia", "sua", "imagem"),
    40801013: ("Radiografia", "sua", "imagem"),
    40101015: ("Colonoscopia", "sua", "nao_imagem"),
    40701121: ("Endoscopia", "sua", "nao_imagem")
}


exam_patterns = {
    "tomografia computadorizada": {
        "pattern": re.compile(r'\b(?:tomografia|tc)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "ressonância magnética": {
        "pattern": re.compile(r'\b(?:ressonancia|rm|ressonância)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "ultrassonografia": {
        "pattern": re.compile(r'\b(?:ultrassom|ultrassonografia)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "radiografia": {
        "pattern": re.compile(r'\b(?:radiografia|raio-x|raiox)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "mamografia": {
        "pattern": re.compile(r'\b(?:mamografia|mamas)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "colonoscopia": {
        "pattern": re.compile(r'\bcolonoscopia\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "nao_imagem"
    },
    "endoscopia": {
        "pattern": re.compile(r'\bendoscopia\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "nao_imagem"
    }
}


ignore_terms = {
    "sem exame", "exame não especificado", "apenas checkup", "sem exame adicional"
}

def normalize_text(txt):
    if not txt:
        return ""


    txt_lower = txt.lower()


    if HAS_UNIDECODE:
        txt_lower = unidecode(txt_lower)


    txt_lower = re.sub(r'\b(adicional|recomendada|programada|do|da|de)\b', '', txt_lower)


    txt_lower = re.sub(r'\s+', ' ', txt_lower).strip()

    return txt_lower

def classify_exam(cd_tuss, ds_receita):

    if cd_tuss and cd_tuss in TUSS_EXAMS:
        return TUSS_EXAMS[cd_tuss]

    norm = normalize_text(ds_receita)  
    if not norm or norm in ignore_terms:
        return ("Sem Exame", "seu", "nao_imagem")


    for cat, info in exam_patterns.items():
        if info["pattern"].search(norm):
            return (cat.title(), info["pronoun"], info["type"])

    return (norm.title(), "seu", "nao_imagem")

def build_message_for_exams(client_name, exam_list):

    unique_image = set()
    unique_non_image = set()

    for (cat, pron, ex_type) in exam_list:
        cat_lower = cat.lower()

        if cat_lower in ignore_terms or cat_lower.startswith("sem exame"):
            continue

        if ex_type == "imagem":
            unique_image.add((cat, pron))
        else:
            unique_non_image.add((cat, pron))


    image_list_str = sorted([f"{pron} {cat}" for (cat, pron) in unique_image])
    non_image_list_str = sorted([f"exame de {cat}" for (cat, pron) in unique_non_image])

    lines = []
    lines.append(f"Olá {client_name},")
    lines.append("")
    lines.append("Identificamos que você tem alguns exames pendentes:")
    lines.append("")

    bullet_lines = []

    for item in image_list_str:
        bullet_lines.append(f"• {item}")
    for item in non_image_list_str:
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

def send_notification(to_number, client_name, exam_list):


    if not to_number.startswith("whatsapp:"):
        to_number = "whatsapp:+55" + to_number

    msg_body = build_message_for_exams(client_name, exam_list)

 
    if TWILIO_ACCOUNT_SID == "TWILIO_ACCOUNT_SID":
        logger.info(f"(Simulação) Mensagem p/ {client_name} ({to_number}):\n{msg_body}")
        return True

    from_number = "whatsapp:+14155238886" if USE_SANDBOX else TWILIO_FROM_NUMBER
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    try:
        message = twilio_client.messages.create(
            from_=from_number,
            body=msg_body,
            to=to_number
        )
        logger.info(f"Mensagem enviada p/ {client_name} ({to_number}). SID={message.sid}")
        return True
    except Exception as e:
        err_str = str(e)
        if "63038" in err_str:
            logger.warning(f"Limite diário atingido para {client_name} ({to_number}). Simulando envio.")
            return True
        else:
            logger.error(f"Erro ao enviar p/ {client_name} ({to_number}): {e}")
            return False

def mark_as_notified_by_tel(conn, tel):

    for tbl in ["dados_estruturados_test", "dados_nao_estruturados_test"]:
        conn.execute(
            text(f"UPDATE public.{tbl} SET notified=true WHERE tel=:tel AND NOT notified"),
            {"tel": tel}
        )
        conn.commit()

def infinite_loop(chunk_size=10, sleep_seconds=30):

    while True:
        logger.info("Iniciando varredura de dados não notificados (tabelas _test)...")
        any_sent = False

        with engine.connect() as conn:

            df1 = pd.read_sql(
                text(
                    "SELECT id, solicitante, tel, ds_receita, cd_tuss "
                    "FROM public.dados_estruturados_test "
                    "WHERE NOT notified "
                    "ORDER BY id LIMIT :lim"
                ),
                conn,
                params={"lim": chunk_size}
            )

            df2 = pd.read_sql(
                text(
                    "SELECT id, solicitante, tel, ds_receita "
                    "FROM public.dados_nao_estruturados_test "
                    "WHERE NOT notified "
                    "ORDER BY id LIMIT :lim"
                ),
                conn,
                params={"lim": chunk_size}
            )

            if df1.empty and df2.empty:
                logger.info("Nenhum registro pendente encontrado. Dormindo...")
                time.sleep(sleep_seconds)
                continue

            df = pd.concat([df1, df2], ignore_index=True)


            grouped = {}
            for _, row in df.iterrows():
                rid = row["id"]
                cd_tuss = row.get("cd_tuss")  
                ds_receita = row.get("ds_receita", "")
                tel = row["tel"]
                solicitante = row["solicitante"]

                cat, pron, ex_type = classify_exam(cd_tuss, ds_receita)


                if "cd_tuss" in row and not pd.isnull(row["cd_tuss"]):
                    table_name = "dados_estruturados_test"
                else:
                    table_name = "dados_nao_estruturados_test"

                if tel not in grouped:
                    grouped[tel] = {
                        "client_name": solicitante,
                        "exams": [],
                        "tables": set()
                    }
                grouped[tel]["exams"].append((cat, pron, ex_type))
                grouped[tel]["tables"].add(table_name)


            for tel, info in grouped.items():
                c_name = info["client_name"]
                exam_list = info["exams"]
                ok = send_notification(tel, c_name, exam_list)
                if ok:
                    any_sent = True

                    mark_as_notified_by_tel(conn, tel)

        if any_sent:
            logger.info("Envios realizados neste ciclo. Retomando em 5s.")
            time.sleep(5)
        else:
            logger.info(f"Nenhum envio realizado neste ciclo. Dormindo {sleep_seconds}s.")
            time.sleep(sleep_seconds)

def main():
    logger.info("Iniciando Loop Infinito de Notificações (Tabelas _test), Mensagem Clean + Filtro + Tel-based Notified.")
    infinite_loop(chunk_size=10, sleep_seconds=30)
    logger.info("Script finalizado (caso loop seja interrompido).")

if __name__ == "__main__":
    main()
