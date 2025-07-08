import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="localhost",
        reload=os.environ.get("DEBUG", False),
        port=int(os.environ.get("PORT", 8000)),
    )
