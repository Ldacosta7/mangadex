import os
from app import create_app
from dotenv import load_dotenv

load_dotenv()



app = create_app()


if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True") == "True"

    print("🎌 MangaBot démarré sur http://localhost:5000")
    app.run(port=port, debug=debug)