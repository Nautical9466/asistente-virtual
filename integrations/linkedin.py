import os

class LinkedInIntegration:
    """LinkedIn integration helper."""

    def __init__(self):
        self.access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")

    def search_jobs(self, keywords: str) -> list:
        return [
            {"title": "AI Assistant Developer", "company": "TechCorp", "location": "Remote"},
            {"title": "Python Backend Engineer", "company": "Innovate Lab", "location": "Remote"},
            {"title": "Automation Specialist", "company": "DataFlow", "location": "Hybrid"}
        ]
