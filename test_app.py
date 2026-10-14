import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app


async def run_tests():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        print("PASS: Health check")

        r = await client.post("/api/todos", json={"title": "Buy groceries", "description": "Milk, eggs, bread"})
        assert r.status_code == 201, f"Create todo failed: {r.text}"
        todo_id = r.json()["id"]
        print(f"PASS: Create todo (id={todo_id})")

        r = await client.post("/api/todos", json={"title": "Call mom"})
        assert r.status_code == 201
        print("PASS: Create second todo")

        r = await client.get("/api/todos")
        assert r.status_code == 200
        todos = r.json()
        assert len(todos) == 2
        print(f"PASS: List todos ({len(todos)} items)")

        r = await client.patch(f"/api/todos/{todo_id}", json={"completed": True})
        assert r.status_code == 200
        assert r.json()["completed"] is True
        print("PASS: Mark todo complete")

        r = await client.delete(f"/api/todos/{todo_id}")
        assert r.status_code == 204
        print("PASS: Delete todo")

        r = await client.get("/api/todos")
        assert len(r.json()) == 1
        print("PASS: Verify deletion")

        r = await client.post("/api/reminders", json={
            "title": "Call dentist",
            "reminder_time": "2026-10-05T10:00:00"
        })
        assert r.status_code == 201
        print("PASS: Create reminder")

        r = await client.get("/api/reminders")
        assert len(r.json()) == 1
        print("PASS: List reminders")

        r = await client.post("/api/calendar", json={
            "title": "Team meeting",
            "start_time": "2026-10-05T14:00:00",
            "end_time": "2026-10-05T15:00:00"
        })
        assert r.status_code == 201
        print("PASS: Create calendar entry")

        r = await client.get("/api/calendar")
        assert len(r.json()) == 1
        print("PASS: List calendar entries")

        r = await client.post("/api/intent", json={"text": "Add walk the dog to my todo list"})
        assert r.status_code == 200
        data = r.json()
        assert "walk the dog" in data["reply"].lower()
        print(f"PASS: Intent parser (create todo) -> {data['reply']}")

        r = await client.post("/api/intent", json={"text": "List my todos"})
        assert r.status_code == 200
        data = r.json()
        assert "walk the dog" in data["reply"].lower()
        print(f"PASS: Intent parser (list todos) -> {data['reply']}")

        r = await client.post("/api/intent", json={"text": "Remind me to water plants at 5pm"})
        assert r.status_code == 200
        data = r.json()
        assert "water plants" in data["reply"].lower()
        print(f"PASS: Intent parser (add reminder) -> {data['reply']}")

        r = await client.post("/api/intent", json={"text": "Schedule a meeting at 3pm"})
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "add_calendar_entry", f"expected add, got {data['action']}"
        assert "meeting" in data["reply"].lower()
        assert "3:00 PM" in data["reply"]
        print(f"PASS: Intent parser (calendar) -> {data['reply']}")

        r = await client.post("/api/intent", json={"text": "list my calendar"})
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "list_calendar", f"expected list, got {data['action']}"
        assert "meeting" in data["reply"].lower()
        print(f"PASS: Intent parser (list calendar) -> {data['reply']}")

        r = await client.post("/api/intent", json={"text": "add buy milk"})
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "create_todo", f"expected create_todo, got {data['action']}"
        assert "buy milk" in data["reply"].lower()
        print(f"PASS: Intent parser (bare add) -> {data['reply']}")

        r = await client.post("/api/intent", json={"text": "remind me to take out the trash tomorrow at 7am"})
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "add_reminder", f"expected add_reminder, got {data['action']}"
        assert "take out the trash" in data["reply"].lower()
        print(f"PASS: Intent parser (remind me) -> {data['reply']}")

        r = await client.post("/api/intent", json={"text": "delete buy milk"})
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "delete_todo", f"expected delete_todo, got {data['action']}"
        assert "buy milk" in data["reply"].lower()
        print(f"PASS: Intent parser (bare delete) -> {data['reply']}")

        r = await client.post("/api/intent", json={"text": "blah blah nonsense"})
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "unknown"
        print("PASS: Intent parser (unknown fallback)")

        r = await client.post("/webhooks/vapi/create-todo", json={
            "name": "create_todo",
            "parameters": {"title": "Vapi test todo"}
        })
        assert r.status_code == 200
        assert "Vapi test todo" in r.json()["result"]
        print(f"PASS: Vapi webhook (create todo) -> {r.json()['result']}")

        r = await client.post("/webhooks/vapi/list-todos", json={
            "name": "list_todos",
            "parameters": {}
        })
        assert r.status_code == 200
        assert "Vapi test todo" in r.json()["result"]
        print(f"PASS: Vapi webhook (list todos) -> {r.json()['result']}")

        r = await client.post("/webhooks/vapi/complete-todo", json={
            "name": "complete_todo",
            "parameters": {"title": "Vapi test todo"}
        })
        assert r.status_code == 200
        assert "completed" in r.json()["result"].lower()
        print(f"PASS: Vapi webhook (complete todo) -> {r.json()['result']}")

        r = await client.post("/webhooks/vapi/delete-todo", json={
            "name": "delete_todo",
            "parameters": {"title": "Vapi test todo"}
        })
        assert r.status_code == 200
        assert "deleted" in r.json()["result"].lower()
        print(f"PASS: Vapi webhook (delete todo) -> {r.json()['result']}")

        r = await client.post("/webhooks/vapi/add-reminder", json={
            "name": "add_reminder",
            "parameters": {"title": "Vapi reminder", "time": "2026-10-05T18:00:00"}
        })
        assert r.status_code == 200
        assert "Vapi reminder" in r.json()["result"]
        print(f"PASS: Vapi webhook (add reminder) -> {r.json()['result']}")

        r = await client.post("/webhooks/vapi/list-reminders", json={
            "name": "list_reminders",
            "parameters": {}
        })
        assert r.status_code == 200
        assert "Vapi reminder" in r.json()["result"]
        print(f"PASS: Vapi webhook (list reminders) -> {r.json()['result']}")

        r = await client.post("/webhooks/vapi/add-calendar-entry", json={
            "name": "add_calendar_entry",
            "parameters": {"title": "Vapi meeting", "start_time": "2026-10-06T10:00:00"}
        })
        assert r.status_code == 200
        assert "Vapi meeting" in r.json()["result"]
        print(f"PASS: Vapi webhook (add calendar) -> {r.json()['result']}")

        r = await client.post("/webhooks/vapi/list-calendar-entries", json={
            "name": "list_calendar_entries",
            "parameters": {}
        })
        assert r.status_code == 200
        assert "Vapi meeting" in r.json()["result"]
        print(f"PASS: Vapi webhook (list calendar) -> {r.json()['result']}")

        print("\nAll tests passed!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_tests())
