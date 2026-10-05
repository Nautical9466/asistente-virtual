import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class GoogleDriveIntegration:
    """Uploads receipt images to Google Drive, automatically organizing them into folders based on Telegram topic names."""

    def __init__(self):
        self.credentials_path = os.environ.get("GOOGLE_DRIVE_CREDENTIALS_JSON", "data/google_drive_credentials.json")
        self.service = None
        self._init_service()

    def _init_service(self):
        if os.path.exists(self.credentials_path):
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                
                scopes = ['https://www.googleapis.com/auth/drive.file']
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path, scopes=scopes
                )
                self.service = build('drive', 'v3', credentials=creds)
                logger.info("✅ Google Drive API initialized with Service Account.")
            except Exception as e:
                logger.warning(f"⚠️ Google Drive API init warning: {e}")
                self.service = None
        else:
            logger.info("ℹ️ GOOGLE_DRIVE_CREDENTIALS_JSON not found. Local drive fallback enabled.")

    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Finds or creates a folder by name in Google Drive."""
        if not self.service:
            return f"local_folder_{folder_name}"

        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])

        if files:
            return files[0]['id']

        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = self.service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

    def upload_receipt(self, file_bytes: bytes, filename: str, topic_name: str) -> str:
        """Uploads a receipt image to Google Drive inside the specific Telegram topic folder."""
        if not self.service:
            # Fallback local folder save if Drive API credentials are not yet uploaded
            local_dir = os.path.join("data", "drive_backup", topic_name.replace(" ", "_"))
            os.makedirs(local_dir, exist_ok=True)
            file_path = os.path.join(local_dir, filename)
            with open(file_path, "wb") as f:
                f.write(file_bytes)
            return f"💾 Guardado localmente en `{file_path}` (Falta GOOGLE_DRIVE_CREDENTIALS_JSON para Drive)"

        try:
            from googleapiclient.http import MediaInMemoryUpload

            root_folder_id = self.get_or_create_folder("Finanzas")
            topic_folder_id = self.get_or_create_folder(topic_name, parent_id=root_folder_id)

            file_metadata = {
                'name': filename,
                'parents': [topic_folder_id]
            }
            media = MediaInMemoryUpload(file_bytes, mimetype='image/jpeg')

            uploaded_file = self.service.files().create(
                body=file_metadata, media_body=media, fields='id, webViewLink'
            ).execute()

            link = uploaded_file.get('webViewLink', uploaded_file.get('id'))
            return f"☁️ Subido a Google Drive: **Finanzas / {topic_name} / {filename}** ([Ver Archivo]({link}))"
        except Exception as e:
            logger.error(f"Error uploading receipt to Google Drive: {e}")
            return f"❌ Error subiendo a Google Drive: {e}"
