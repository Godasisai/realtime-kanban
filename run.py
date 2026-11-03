import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("  * Julley Online Collaborative Kanban Board")
    print("  Multi-Organization + Multi-Tenant Architecture with Live WebSockets")
    print("=" * 70)
    print("  Web Application:     http://localhost:8000")
    print("  Swagger API Docs:    http://localhost:8000/docs")
    print("  ReDoc Documentation: http://localhost:8000/redoc")
    print("  WebSocket Endpoint:  ws://localhost:8000/ws")
    print("-" * 70)
    print("  Seeded Demo Personas (Password: password123):")
    print("     1. sai@julley.com    -> Org Admin (Julley Online - All Branches)")
    print("     2. priya@julley.com  -> Tenant Admin (Bangalore HQ)")
    print("     3. rahul@julley.com  -> Member (Bangalore HQ)")
    print("     4. ananya@julley.com -> Tenant Admin (Hyderabad Hub)")
    print("     5. john@acme.com     -> Org Admin (Acme Cloud - Isolated Org)")
    print("=" * 70)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
