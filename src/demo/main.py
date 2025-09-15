import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from website import create_app

app = create_app()

if __name__ == "__main__":
    print("ok")
    app.run(host="0.0.0.0",debug=True)


