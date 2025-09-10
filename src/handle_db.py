# handle_db.py  (Supabase version)
"""
Módulo de acesso a dados adaptado para Supabase (Postgres remoto).

Observação: variáveis de ambiente (SUPABASE_URL / SUPABASE_KEY) devem ser
carregadas antes de chamar funções deste módulo. O main.py agora faz isso
priorizando .env externo e .env embutido.
"""

import os
from datetime import datetime
import logging
import pytz

try:
    from supabase import create_client, Client
except Exception as e:
    raise ImportError("Biblioteca 'supabase' não encontrada. Instale com: pip install supabase") from e

# Configure logging simples
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE_NAME = "atividades"
TIMEZONE = pytz.timezone('America/Sao_Paulo')

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS public.{TABLE_NAME} (
  id bigserial PRIMARY KEY,
  tipo_atividade text NOT NULL,
  descricao text,
  inicio timestamp without time zone NOT NULL,
  fim timestamp without time zone,
  user_id text,
  ano integer,
  mes integer,
  dia integer,
  horas_trabalhadas numeric
);
"""

def get_supabase_client():
    """Cria e retorna o client do Supabase usando variáveis de ambiente."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_KEY devem estar definidas como variáveis de ambiente.")
    client = create_client(url, key)
    return client

def setup_database():
    supabase = get_supabase_client()
    try:
        resp = supabase.table(TABLE_NAME).select("id").limit(1).execute()
        if getattr(resp, "error", None):
            logger.warning("Erro ao acessar tabela '%s': %s", TABLE_NAME, resp.error)
            return {"exists": False, "create_table_sql": CREATE_TABLE_SQL}
        check_columns = supabase.table(TABLE_NAME).select("ano, mes, dia, horas_trabalhadas").limit(1).execute()
        if getattr(check_columns, "error", None):
            logger.warning("Tabela existe mas faltam colunas. Execute este SQL no Supabase:\n%s", 
                          "ALTER TABLE atividades ADD COLUMN ano integer, ADD COLUMN mes integer, ADD COLUMN dia integer, ADD COLUMN horas_trabalhadas numeric;")
        logger.info("Tabela '%s' acessível no Supabase.", TABLE_NAME)
        return {"exists": True}
    except Exception as e:
        logger.exception("Falha ao verificar tabela '%s': %s", TABLE_NAME, e)
        return {"exists": False, "create_table_sql": CREATE_TABLE_SQL}

def calcular_horas_trabalhadas(inicio, fim):
    if not fim:
        return None
    diferenca = fim - inicio
    horas = diferenca.total_seconds() / 3600
    return round(horas, 10)

def iniciar_nova_atividade(tipo, descricao, user_id, supabase_client: Client = None):
    if not supabase_client:
        supabase_client = get_supabase_client()

    hora_inicio = datetime.now(TIMEZONE)
    hora_inicio_iso = hora_inicio.isoformat()
    ano = hora_inicio.year
    mes = hora_inicio.month
    dia = hora_inicio.day

    payload = {
        "tipo_atividade": tipo,
        "descricao": descricao,
        "inicio": hora_inicio_iso,
        "user_id": user_id,
        "ano": ano,
        "mes": mes,
        "dia": dia,
        "horas_trabalhadas": None
    }

    resp = supabase_client.table(TABLE_NAME).insert(payload).execute()
    if getattr(resp, "error", None):
        logger.error("Erro ao inserir atividade: %s", resp.error)
        raise RuntimeError(f"Supabase insert error: {resp.error}")

    data = getattr(resp, "data", None)
    if data and isinstance(data, list) and len(data) > 0:
        inserted = data[0]
        return inserted.get("id", None)
    return None

def finalizar_atividade(activity_id, supabase_client: Client = None):
    if not supabase_client:
        supabase_client = get_supabase_client()

    atividade = supabase_client.table(TABLE_NAME).select("inicio").eq("id", activity_id).execute()
    if getattr(atividade, "error", None):
        logger.error("Erro ao buscar atividade id=%s: %s", activity_id, atividade.error)
        raise RuntimeError(f"Supabase select error: {atividade.error}")
    if not atividade.data:
        logger.error("Atividade id=%s não encontrada.", activity_id)
        raise RuntimeError("Atividade não encontrada.")

    inicio_str = atividade.data[0]["inicio"]
    inicio = datetime.fromisoformat(inicio_str.replace('Z', '+00:00')).astimezone(TIMEZONE)
    fim = datetime.now(TIMEZONE)
    fim_iso = fim.isoformat()
    horas_trabalhadas = calcular_horas_trabalhadas(inicio, fim)

    resp = supabase_client.table(TABLE_NAME).update({
        "fim": fim_iso,
        "horas_trabalhadas": horas_trabalhadas
    }).eq("id", activity_id).execute()

    if getattr(resp, "error", None):
        logger.error("Erro ao finalizar atividade id=%s: %s", activity_id, resp.error)
        raise RuntimeError(f"Supabase update error: {resp.error}")
    return True

def buscar_atividade_em_andamento(user_id=None, supabase_client: Client = None):
    if not supabase_client:
        supabase_client = get_supabase_client()

    query = supabase_client.table(TABLE_NAME).select("*").is_("fim", None).order("id", desc=True).limit(1)
    if user_id is not None:
        query = query.eq("user_id", user_id)

    resp = query.execute()
    if getattr(resp, "error", None):
        logger.error("Erro ao buscar atividade em andamento: %s", resp.error)
        raise RuntimeError(f"Supabase select error: {resp.error}")

    data = getattr(resp, "data", None)
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return None

def listar_atividades(limit: int = 100, user_id=None, supabase_client: Client = None):
    if not supabase_client:
        supabase_client = get_supabase_client()

    query = supabase_client.table(TABLE_NAME).select("*").order("id", desc=True).limit(limit)
    if user_id is not None:
        query = query.eq("user_id", user_id)
    resp = query.execute()
    if getattr(resp, "error", None):
        logger.error("Erro ao listar atividades: %s", resp.error)
        raise RuntimeError(f"Supabase select error: {resp.error}")
    return getattr(resp, "data", []) or []
