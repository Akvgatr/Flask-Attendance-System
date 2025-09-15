import os, sys
from dotenv import load_dotenv
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from website import create_app

# Load .env only locally
load_dotenv()

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
