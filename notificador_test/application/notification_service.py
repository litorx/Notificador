import time
import logging
import pandas as pd
from sqlalchemy import text
from infrastructure.database import engine, mark_as_notified_by_tel
from domain.exam_utils import classify_exam
from infrastructure.twilio_client import send_notification

logger = logging.getLogger("notifier")

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
                    grouped[tel] = {"client_name": solicitante, "exams": [], "tables": set()}
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
