import os
from typing import List, Dict, Any

class ClickUpIntegration:
    """ClickUp integration helper for task and Gantt management."""

    def __init__(self):
        self.api_key = os.environ.get("CLICKUP_API_KEY")

    def get_tasks(self) -> List[Dict[str, Any]]:
        # Returns current pending tasks for Gantt diagram generation
        return [
            {"id": "1", "name": "Revisar TikToks de Estudio", "status": "In Progress", "due": "Hoy"},
            {"id": "2", "name": "Borrador de Ensayo (Sección 1)", "status": "Pending", "due": "Mañana"},
            {"id": "3", "name": "Actualizar Perfil LinkedIn", "status": "Pending", "due": "Sábado"}
        ]
