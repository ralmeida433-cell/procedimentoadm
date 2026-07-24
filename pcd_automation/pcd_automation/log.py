"""Log de alterações por etapa do processo (requisito de segurança/auditoria).

Cada evento é uma linha JSON em `logs/<processo_id>.jsonl`, apensada
(nunca sobrescrita), com timestamp, etapa e detalhes.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def registrar_evento(caminho_log: Path, etapa: str, detalhes: dict, nivel: str = "INFO") -> None:
    caminho_log = Path(caminho_log)
    caminho_log.parent.mkdir(parents=True, exist_ok=True)
    linha = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "nivel": nivel,
        "etapa": etapa,
        "detalhes": detalhes,
    }
    with open(caminho_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False, default=str) + "\n")
