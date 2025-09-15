import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from website import create_app

app = create_app()

if __name__ == "__main__":
    print("ok")
    port = int(os.environ.get("PORT", 5000))  # Use Render's port
    app.run(host="0.0.0.0", port=port, debug=True)
