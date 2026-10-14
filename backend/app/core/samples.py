"""Built-in inventories used by the sample endpoint. Not a benchmark set."""

SURFACE_SAMPLE = {
    "application": "lane-desk",
    "surfaces": [
        {
            "id": "notes.create",
            "kind": "ipc",
            "module": "notes",
            "handler": "createNote",
            "summary": "Create a note",
            "params": [
                {"name": "title", "type": "string", "required": True},
                {"name": "body", "type": "string", "required": False},
            ],
        },
        {
            "id": "notes.search",
            "kind": "ipc",
            "module": "notes",
            "handler": "searchNotes",
            "summary": "Search notes",
            "params": [{"name": "query", "type": "string", "required": True}],
        },
        {
            "id": "meetings.schedule",
            "kind": "ipc",
            "module": "meetings",
            "handler": "scheduleMeeting",
            "summary": "Schedule a meeting",
            "params": [
                {"name": "title", "type": "string", "required": True},
                {"name": "startsAt", "type": "string", "required": True},
            ],
        },
        {
            "id": "meetings.cancel",
            "kind": "ipc",
            "module": "meetings",
            "handler": "cancelMeeting",
            "summary": "Cancel a meeting",
            "params": [{"name": "meetingId", "type": "string", "required": True}],
        },
        {
            "id": "files.export",
            "kind": "function",
            "module": "files",
            "handler": "exportMinutes",
            "summary": "Export meeting minutes",
            "params": [
                {"name": "meetingId", "type": "string", "required": True},
                {"name": "format", "type": "string", "required": False},
            ],
        },
        {
            "id": "orders.list",
            "kind": "http",
            "module": "orders",
            "handler": "listOrders",
            "summary": "List orders",
            "method": "GET",
            "path": "/orders",
            "params": [],
        },
    ],
}

PYTHON_SAMPLE = {
    "application": "lane-desk",
    "files": [
        {
            "path": "notes.py",
            "source": (
                "def create_note(title: str, body: str = \"\"):\n"
                "    return title\n"
                "\n"
                "def search_notes(query: str):\n"
                "    return query\n"
                "\n"
                "def _hidden():\n"
                "    return None\n"
            ),
        },
        {
            "path": "orders.py",
            "source": (
                "app = object()\n"
                "\n"
                "@app.get(\"/orders\")\n"
                "def list_orders():\n"
                "    return []\n"
                "\n"
                "@app.post(\"/orders\")\n"
                "def create_order(sku: str, quantity: int = 1):\n"
                "    return sku\n"
            ),
        },
    ],
}
