from __future__ import annotations

from typing import Dict, Any
from jinja2 import Environment, DictLoader, select_autoescape


TEMPLATES_EN = {
    "Open": "Request {{id}} ({{type}}) is Open with {{dept}}. Estimated completion: {{eta}}. We'll notify you of updates.",
    "In Progress": "Request {{id}} ({{type}}) is In Progress with {{dept}}. Estimated completion: {{eta}}.",
    "Closed": "Request {{id}} ({{type}}) was Closed by {{dept}}. Thank you for helping improve our city!",
    "Default": "Request {{id}} ({{type}}) status: {{status}} with {{dept}}. ETA: {{eta}}.",
}

TEMPLATES_ES = {
    "Open": "La solicitud {{id}} ({{type}}) está Abierta con {{dept}}. Tiempo estimado de finalización: {{eta}}. Le avisaremos de actualizaciones.",
    "In Progress": "La solicitud {{id}} ({{type}}) está En Progreso con {{dept}}. Tiempo estimado de finalización: {{eta}}.",
    "Closed": "La solicitud {{id}} ({{type}}) fue Cerrada por {{dept}}. ¡Gracias por ayudar a mejorar la ciudad!",
    "Default": "La solicitud {{id}} ({{type}}) tiene estado: {{status}} con {{dept}}. ETA: {{eta}}.",
}


env_en = Environment(loader=DictLoader(TEMPLATES_EN), autoescape=select_autoescape())
env_es = Environment(loader=DictLoader(TEMPLATES_ES), autoescape=select_autoescape())


def render_update(ticket: Dict[str, Any], eta: Dict[str, Any], lang: str = "en") -> str:
    status = (ticket.get("Status") or "").strip() or "Default"
    key = status if status in TEMPLATES_EN else "Default"
    data = {
        "id": ticket.get("Request_ID"),
        "type": ticket.get("Request_Type") or "",
        "dept": ticket.get("Department") or "the assigned department",
        "status": ticket.get("Status") or "",
        "eta": eta.get("eta_range_label") or "not available",
    }
    if lang.lower().startswith("es"):
        tmpl = env_es.get_template(key)
    else:
        tmpl = env_en.get_template(key)
    return tmpl.render(**data)
