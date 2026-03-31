"""
Seed script: populates the database with realistic logs for multiple simulated users.
No internal user accounts — user_id is any identifier the calling system provides.

Run with: python -m scripts.seed_data
"""
import asyncio
import random
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database import connect_db, close_db, get_db
from app.services.embedding_service import build_index, get_embedding_model
from app.models.log import LogEntry, LogCategory


# Simulated external user identifiers (these come from the calling system —
# could be UUIDs, database PKs, JWT subjects, session tokens, etc.)
USERS = [
    "usr_jayzheej_001",   # UUID-style
    "usr_alice_002",
    "usr_bob_003",
]

# Richer log templates with descriptions for better AI context
LOG_TEMPLATES = [
    {
        "module": "auth", "action": "user_login", "category": "AUTH", "entity": "session",
        "description": "User successfully authenticated using password",
        "meta": {"method": "password", "success": True, "ip": "192.168.1.10"},
    },
    {
        "module": "auth", "action": "user_login_failed", "category": "ERROR", "entity": "session",
        "description": "Authentication failed due to incorrect password",
        "meta": {"method": "password", "success": False, "reason": "wrong_password", "attempts": 3},
    },
    {
        "module": "auth", "action": "user_logout", "category": "AUTH", "entity": "session",
        "description": "User ended their session voluntarily",
        "meta": {"session_duration_min": 45},
    },
    {
        "module": "auth", "action": "token_refresh", "category": "AUTH", "entity": "token",
        "description": "Access token refreshed before expiry",
        "meta": {"previous_expiry": "1h", "new_expiry": "1h"},
    },
    {
        "module": "inventory", "action": "create_item", "category": "CRUD", "entity": "product",
        "description": "New product added to inventory",
        "meta": {"product_id": "P-1001", "name": "Wireless Mouse", "price": 29.99, "stock": 100},
    },
    {
        "module": "inventory", "action": "update_stock", "category": "CRUD", "entity": "product",
        "description": "Stock level adjusted after sale",
        "meta": {"product_id": "P-1001", "old_stock": 50, "new_stock": 45, "reason": "sale"},
    },
    {
        "module": "inventory", "action": "delete_item", "category": "CRUD", "entity": "product",
        "description": "Product removed from inventory — discontinued",
        "meta": {"product_id": "P-1002", "name": "USB Cable", "reason": "discontinued"},
    },
    {
        "module": "inventory", "action": "bulk_import", "category": "CRUD", "entity": "product",
        "description": "Bulk product import from CSV upload completed",
        "meta": {"count": 150, "source": "csv_upload", "failed": 2},
    },
    {
        "module": "orders", "action": "create_order", "category": "CRUD", "entity": "order",
        "description": "New customer order placed successfully",
        "meta": {"order_id": "ORD-5001", "total": 129.99, "items": 3, "payment": "card"},
    },
    {
        "module": "orders", "action": "update_order_status", "category": "CRUD", "entity": "order",
        "description": "Order status updated from pending to shipped",
        "meta": {"order_id": "ORD-5001", "old_status": "pending", "new_status": "shipped", "tracking": "TRK-9021"},
    },
    {
        "module": "orders", "action": "cancel_order", "category": "CRUD", "entity": "order",
        "description": "Order cancelled at customer request before shipment",
        "meta": {"order_id": "ORD-5002", "reason": "customer_request", "refund_triggered": True},
    },
    {
        "module": "orders", "action": "refund_processed", "category": "CRUD", "entity": "payment",
        "description": "Refund of $49.99 processed for cancelled order",
        "meta": {"order_id": "ORD-5002", "amount": 49.99, "currency": "USD", "method": "original_payment"},
    },
    {
        "module": "reports", "action": "generate_sales_report", "category": "QUERY", "entity": "report",
        "description": "Monthly sales report generated for Feb 2026",
        "meta": {"period": "monthly", "month": "2026-02", "rows": 4200, "duration_ms": 1840},
    },
    {
        "module": "reports", "action": "export_csv", "category": "QUERY", "entity": "report",
        "description": "Report exported to CSV format",
        "meta": {"rows": 1200, "file_size_kb": 340, "format": "csv"},
    },
    {
        "module": "system", "action": "backup_completed", "category": "SYSTEM", "entity": "backup",
        "description": "Full system backup completed successfully to S3",
        "meta": {"type": "full", "duration_sec": 340, "size_mb": 512, "target": "s3://backups/2026"},
    },
    {
        "module": "system", "action": "service_restart", "category": "SYSTEM", "entity": "service",
        "description": "Worker queue service restarted due to out-of-memory error",
        "meta": {"service": "worker-queue", "reason": "OOM", "memory_mb_at_crash": 2048},
    },
    {
        "module": "system", "action": "health_check", "category": "SYSTEM", "entity": "monitor",
        "description": "Automated health check — all services nominal",
        "meta": {"cpu": "23%", "memory": "61%", "disk": "44%", "status": "healthy"},
    },
    {
        "module": "api", "action": "rate_limit_exceeded", "category": "ERROR", "entity": "gateway",
        "description": "Client exceeded API rate limit of 100 requests/min",
        "meta": {"ip": "192.168.1.55", "endpoint": "/api/v1/search", "limit": 100, "actual": 143},
    },
    {
        "module": "api", "action": "internal_server_error", "category": "ERROR", "entity": "handler",
        "description": "Unhandled exception in order service caused 500 error",
        "meta": {"endpoint": "/api/v1/orders", "trace": "NullPointerException at OrderService:142", "status": 500},
    },
    {
        "module": "api", "action": "timeout", "category": "ERROR", "entity": "handler",
        "description": "Report export request timed out after 30 seconds",
        "meta": {"endpoint": "/api/v1/reports/export", "timeout_ms": 30000, "status": 504},
    },
    {
        "module": "notifications", "action": "send_email", "category": "API", "entity": "email",
        "description": "Order confirmation email sent to customer",
        "meta": {"template": "order_confirmation", "status": "delivered", "latency_ms": 210},
    },
    {
        "module": "notifications", "action": "webhook_dispatch", "category": "API", "entity": "webhook",
        "description": "Webhook dispatched to partner system for order event",
        "meta": {"url": "https://partner.example.com/hook", "status": 200, "retry": 0},
    },
    {
        "module": "payments", "action": "charge_card", "category": "API", "entity": "payment",
        "description": "Card payment of $129.99 processed successfully",
        "meta": {"amount": 129.99, "currency": "USD", "status": "success", "processor": "stripe"},
    },
    {
        "module": "payments", "action": "charge_failed", "category": "ERROR", "entity": "payment",
        "description": "Card charge failed due to insufficient funds",
        "meta": {"amount": 49.99, "currency": "USD", "reason": "insufficient_funds", "decline_code": "card_declined"},
    },
    {
        "module": "users", "action": "update_profile", "category": "CRUD", "entity": "user",
        "description": "User updated their email address",
        "meta": {"field": "email", "old": "old@mail.com", "new": "new@mail.com"},
    },
    {
        "module": "users", "action": "enable_2fa", "category": "AUTH", "entity": "user",
        "description": "Two-factor authentication enabled by user",
        "meta": {"method": "totp", "app": "google_authenticator"},
    },
]


def random_ts(days_back: int = 14) -> datetime:
    return datetime.utcnow() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


async def seed():
    print("Connecting to MongoDB...")
    db = await connect_db()

    await db.logs.delete_many({})
    await db.chat_sessions.delete_many({})
    print("Cleared existing logs and chat sessions.")

    all_entries = []
    for _ in range(150):
        tpl = random.choice(LOG_TEMPLATES)
        uid = random.choice(USERS)
        entry = LogEntry(
            timestamp=random_ts(),
            user_id=uid,
            module=tpl["module"],
            action=tpl["action"],
            entity=tpl.get("entity"),
            category=LogCategory(tpl["category"]),
            description=tpl.get("description"),
            metadata=tpl.get("meta", {}),
            system_context={"ip": f"10.0.{random.randint(0,5)}.{random.randint(1,254)}", "source": "seed"},
        )
        entry.embedding_text = entry.to_embedding_string()
        all_entries.append(entry)

    await db.logs.insert_many([e.model_dump() for e in all_entries])
    print(f"  Inserted {len(all_entries)} log entries across {len(USERS)} users.")

    print("Building FAISS embedding index...")
    get_embedding_model()
    log_docs = await db.logs.find({}, {"_id": 0}).to_list(length=5000)
    build_index(log_docs)
    print(f"  FAISS index built with {len(log_docs)} entries.")

    await close_db()
    print("\nSeed complete!")
    print("  API Key: systemassist-dev-key-change-in-production")
    print("  Test user IDs:")
    for uid in USERS:
        print(f"    {uid}")
    print("\n  All endpoints require: X-Api-Key header")
    print("  user_id is passed in the request body (not from auth token)")


if __name__ == "__main__":
    asyncio.run(seed())
