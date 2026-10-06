import os
import json
from dotenv import load_dotenv
from integrations.outlook import OutlookIntegration

load_dotenv()
outlook = OutlookIntegration()
res = outlook.get_tasks()
print("=== LIVE OUTLOOK TASKS FROM MICROSOFT GRAPH API ===")
print(res[:2000])
