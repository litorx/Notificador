from sqlalchemy import create_engine, text
from config.settings import DATABASE_URL

# Conexão com o Banco de Dados
engine = create_engine(DATABASE_URL)

def mark_as_notified_by_tel(conn, tel):
    """
    Marca todos os registros (notified=false) para esse telefone
    em 'dados_estruturados' e 'dados_nao_estruturados' como notified=true.
    """
    for tbl in ["dados_estruturados", "dados_nao_estruturados"]:
        conn.execute(
            text(f"UPDATE public.{tbl} SET notified=true WHERE tel=:tel AND NOT notified"),
            {"tel": tel}
        )
        conn.commit()
