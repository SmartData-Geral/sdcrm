from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    "Agora" em UTC **naive**.

    O framework grava datetime.utcnow (naive) em colunas declaradas
    DateTime(timezone=True) -- ver core/columns.py -- enquanto oportunidade_service
    grava valores aware. Misturar os dois faz comparações de data (o agendamento de
    retry de webhook, por exemplo) falharem silenciosamente. Todo código novo desta
    trilha de integração usa este helper e nada mais.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
