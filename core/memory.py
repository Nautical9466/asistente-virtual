import os
import json
from datetime import datetime
from typing import List, Dict, Any

class MemoryManager:
    """Manages chat history and user context persistence."""

    def __init__(self, data_file: str = "data/context.json", max_history: int = 20):
        self.data_file = data_file
        self.max_history = max_history
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self.load()

    def load(self):
        """Loads stored context from data file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"[MemoryManager] Error loading context: {e}")
                self.history = {}
        else:
            self.history = {}

    def save(self):
        """Saves context to data file."""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[MemoryManager] Error saving context: {e}")

    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns recent chat history for given user."""
        return self.history.get(user_id, [])[-self.max_history:]

    def add_interaction(self, user_id: str, user_text: str, assistant_text: str):
        """Appends a new interaction to user history and saves."""
        if user_id not in self.history:
            self.history[user_id] = []

        now = datetime.now().isoformat()
        self.history[user_id].append({"role": "user", "content": user_text, "timestamp": now})
        self.history[user_id].append({"role": "assistant", "content": assistant_text, "timestamp": now})

        # Trim history if exceeding limit
        if len(self.history[user_id]) > self.max_history * 2:
            self.history[user_id] = self.history[user_id][-self.max_history * 2:]

        self.save()

    def clear(self, user_id: str):
        """Clears history for given user."""
        if user_id in self.history:
            self.history[user_id] = []
            self.save()
