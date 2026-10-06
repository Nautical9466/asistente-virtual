import unittest
import os
from main import handle_incoming_message
from core.mcp_tools import mcp_registry

class TestVirtualAssistant(unittest.TestCase):

    def test_mcp_tools_schema(self):
        schema = mcp_registry.get_tools_schema()
        tool_names = [t["function"]["name"] for t in schema]
        self.assertIn("create_outlook_task", tool_names)
        self.assertIn("create_calendar_event", tool_names)
        self.assertIn("get_calendar_events", tool_names)

    def test_incoming_message_fallback(self):
        msg = "Hola Claudia, ¿cuáles son tus capacidades?"
        res = handle_incoming_message(msg, "test_user")
        self.assertIsInstance(res, str)
        self.assertTrue(len(res) > 0)

if __name__ == "__main__":
    unittest.main()
