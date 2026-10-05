import os

class ObsidianSync:
    """Helper for syncing notes and summaries with an Obsidian Vault."""

    def __init__(self, vault_path: str = "vault"):
        self.vault_path = vault_path

    def save_note(self, title: str, content: str, category: str = "General") -> str:
        folder = os.path.join(self.vault_path, category)
        os.makedirs(folder, exist_ok=True)
        filename = f"{title.replace(' ', '_').lower()}.md"
        filepath = os.path.join(folder, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{content}\n")

        return filepath
