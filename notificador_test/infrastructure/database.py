from sqlalchemy import create_engine, text
from config.settings import DATABASE_URL


engine = create_engine(DATABASE_URL)

def mark_as_notified_by_tel(conn, tel):
    """
    Atualiza os registros (notified=false) para o telefone informado nas tabelas _test
    definindo notified=true.
    """
    for tbl in ["dados_estruturados_test", "dados_nao_estruturados_test"]:
        conn.execute(
            text(f"UPDATE public.{tbl} SET notified=true WHERE tel=:tel AND NOT notified"),
            {"tel": tel}
        )
        conn.commit()
