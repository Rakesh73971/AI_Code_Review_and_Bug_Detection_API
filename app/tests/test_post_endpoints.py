import io
import os
import sys
import time
import zipfile
import subprocess
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://127.0.0.1:8001"
TEST_ADMIN_EMAIL = f"admin_{int(time.time())}@example.com"
TEST_ADMIN_PASSWORD = "StrongPassword123"
TEST_USER_EMAIL = f"user_{int(time.time())}@example.com"
TEST_USER_PASSWORD = "UserPassword123"

def is_server_running():
    try:
        response = httpx.get(f"{BASE_URL}/")
        return response.status_code == 200
    except httpx.RequestError:
        return False

def create_dummy_zip():
    """Creates a dummy codebase ZIP file in-memory for testing the upload endpoint."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        # Add a python file
        zip_file.writestr(
            "app/utils.py",
            "def add_numbers(a, b):\n    return a + b\n\ndef divide_numbers(a, b):\n    return a / b  # Warning: Potential ZeroDivisionError\n"
        )
        # Add a javascript file
        zip_file.writestr(
            "frontend/index.js",
            "function greet(name) {\n    console.log('Hello, ' + name);\n}\n"
        )
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def run_tests():
    server_process = None
    if not is_server_running():
        print("[*] FastAPI server is not running on port 8001. Starting uvicorn dynamically...")
        # Start uvicorn using the virtual environment's executable if possible
        python_exe = sys.executable
        server_process = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "app.main:app", "--port", "8001"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Wait for the server to boot up
        for i in range(15):
            print(f"[*] Waiting for server to start ({i+1}/15)...")
            time.sleep(1)
            if is_server_running():
                print("[+] Server started successfully on port 8001!")
                break
        else:
            print("[-] Error: Failed to start uvicorn on port 8001.")
            if server_process:
                # print output logs to help diagnose
                stdout, stderr = server_process.communicate(timeout=1.0)
                print("--- Server Stdout ---")
                print(stdout)
                print("--- Server Stderr ---")
                print(stderr)
                server_process.terminate()
            sys.exit(1)
    else:
        print("[+] FastAPI server is already running on http://127.0.0.1:8001")

    client = httpx.Client(base_url=BASE_URL, timeout=120.0)

    try:
        # ==========================================
        # 1. POST /users/ - Create Admin User
        # ==========================================
        print("\n--- 1. POST /users/ (Create Admin User) ---")
        admin_payload = {
            "username": "testadmin",
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD,
            "role": "admin",
            "github_name": "testadmin_git",
            "is_active": True
        }
        res = client.post("/users/", json=admin_payload)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")
        if res.status_code != 201:
            print("[-] Registration failed. Exiting.")
            return

        # ==========================================
        # 2. POST /login - Authenticate Admin
        # ==========================================
        print("\n--- 2. POST /login (Admin Login) ---")
        login_data = {
            "username": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD
        }
        res = client.post("/login", data=login_data)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")
        if res.status_code != 200:
            print("[-] Login failed. Exiting.")
            return
        
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # ==========================================
        # 3. POST /users/ - Create Regular User
        # ==========================================
        print("\n--- 3. POST /users/ (Create Regular User) ---")
        user_payload = {
            "username": "testuser",
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "role": "user",
            "github_name": "testuser_git",
            "is_active": True
        }
        res = client.post("/users/", json=user_payload)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")

        # ==========================================
        # 4. POST /rag/index-docs - Index Official Docs (Admin Only)
        # ==========================================
        print("\n--- 4. POST /rag/index-docs (Index Documentation - Admin Only) ---")
        print("[*] Triggering web loader documentation indexing. This may take a few seconds...")
        res = client.post("/rag/index-docs", headers=headers)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")

        # ==========================================
        # 5. POST /sessions/upload - Upload Codebase Zip
        # ==========================================
        print("\n--- 5. POST /sessions/upload (Upload & Index Codebase ZIP) ---")
        zip_data = create_dummy_zip()
        files = {"file": ("codebase.zip", zip_data, "application/zip")}
        data = {"project_name": "Demo Codebase Project"}
        res = client.post("/sessions/upload", headers=headers, data=data, files=files)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")
        
        session_id = None
        if res.status_code == 201:
            session_id = res.json().get("id")

        # ==========================================
        # 6. POST /sessions/ - Create Session Manually
        # ==========================================
        print("\n--- 6. POST /sessions/ (Create Codebase Session Manually) ---")
        session_payload = {
            "project_name": f"Manual session project {int(time.time())}",
            "chroma_collection_id": f"manual_col_{int(time.time())}",
            "file_count": 2,
            "status": "ready",
            "task_id": f"task_manual_xyz_{int(time.time())}"
        }
        res = client.post("/sessions/", headers=headers, json=session_payload)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")

        # ==========================================
        # 7. POST /sessions/{session_id}/ask - Chat with Codebase
        # ==========================================
        if session_id:
            print(f"\n--- 7. POST /sessions/{session_id}/ask (Ask Codebase Q&A) ---")
            chat_payload = {
                "question": "What function is defined in utils.py?"
            }
            res = client.post(f"/sessions/{session_id}/ask", headers=headers, json=chat_payload)
            print(f"Status Code: {res.status_code}")
            print(f"Response: {res.text}")

        # ==========================================
        # 8. POST /sessions/{session_id}/messages/ - Add Manual Message
        # ==========================================
        if session_id:
            print(f"\n--- 8. POST /sessions/{session_id}/messages/ (Create Chat Message Manually) ---")
            msg_payload = {
                "role": "user",
                "content": "Check codebase structure review",
                "doc_sources": [{"source": "utils.py"}]
            }
            res = client.post(f"/sessions/{session_id}/messages/", headers=headers, json=msg_payload)
            print(f"Status Code: {res.status_code}")
            print(f"Response: {res.text}")

        # ==========================================
        # 9. POST /code-reviews/analyze - Analyze Code Snippet
        # ==========================================
        print("\n--- 9. POST /code-reviews/analyze (AI Code Review Analysis) ---")
        review_req_payload = {
            "language": "python",
            "original_code": "def divide(x, y):\n    return x / y\n",
            "use_rag": True
        }
        res = client.post("/code-reviews/analyze", headers=headers, json=review_req_payload)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")

        # ==========================================
        # 10. POST /code-reviews/ - Create Manual Review Record
        # ==========================================
        print("\n--- 10. POST /code-reviews/ (Create Code Review Record Manually) ---")
        review_create_payload = {
            "language": "python",
            "original_code": "def divide(x, y):\n    return x / y\n",
            "bugs_found": [
                {
                    "line": 2,
                    "severity": "warning",
                    "description": "Division by zero possibility if y is 0.",
                    "suggested_fix": "def divide(x, y):\n    if y == 0:\n        raise ValueError('Division by zero')\n    return x / y"
                }
            ],
            "severity_summary": {
                "critical": 0,
                "warning": 1,
                "info": 0
            },
            "suggestions": ["Add input validation to prevent DivisionByZero exception."],
            "quality_score": 75,
            "doc_sources_used": ["errors.html"],
            "source": "MANUAL",
            "github_pr_url": None
        }
        res = client.post("/code-reviews/", headers=headers, json=review_create_payload)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")

        # ==========================================
        # 11. POST /webhooks/github - Test Mock GitHub Webhook
        # ==========================================
        print("\n--- 11. POST /webhooks/github (Test Mock GitHub PR Webhook) ---")
        webhook_headers = {
            "X-GitHub-Event": "pull_request"
        }
        mock_webhook_payload = {
            "action": "opened",
            "number": 42,
            "repository": {
                "name": "Bank_API",
                "owner": {
                    "login": "testowner"
                },
                "full_name": "testowner/Bank_API"
            },
            "pull_request": {
                "head": {
                    "sha": "mocksha123abcdef"
                },
                "html_url": "https://github.com/testowner/Bank_API/pull/42",
                "user": {
                    "login": "testadmin_git"
                }
            }
        }
        res = client.post("/webhooks/github", headers=webhook_headers, json=mock_webhook_payload)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")

        # ==========================================
        # 12. GET /code-reviews/analytics - Get Platform Bug Analytics
        # ==========================================
        print("\n--- 12. GET /code-reviews/analytics (Get Admin Bug Analytics) ---")
        res = client.get("/code-reviews/analytics", headers=headers)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")

    except Exception as e:
        print(f"\n[-] Testing encountered an exception: {e}")
    finally:
        client.close()
        if server_process:
            print("\n[*] Terminating uvicorn subprocess...")
            server_process.terminate()
            stdout, stderr = server_process.communicate()
            print("--- Server Stdout (Logs) ---")
            print(stdout)
            print("--- Server Stderr (Logs) ---")
            print(stderr)
            print("[+] Subprocess terminated. Tests complete.")

if __name__ == "__main__":
    run_tests()
