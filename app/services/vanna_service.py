from vanna.ollama import Ollama
from vanna.chromadb import ChromaDB_VectorStore
from app.config import settings
import os


class VannaService(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None) -> None:
        ChromaDB_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)


def train_vanna_instance() -> VannaService:
    """Train Vanna instance."""
    vn = get_vanna_instance()

    ddls = vn.run_sql("SELECT type, sql FROM sqlite_master WHERE sql is not null")
    for ddl in ddls["sql"].to_list():
        vn.train(ddl=ddl)


def get_vanna_instance() -> VannaService:
    """Get configured Vanna instance."""
    cdir = os.getcwd()
    vn = VannaService(
        config={
            "model": settings.model_name,
            "path": os.path.join(cdir, settings.chroma_folder),
            "options": {
                "num_ctx": 4096,
            },
        }
    )

    vn.connect_to_sqlite(settings.sqlite_path)
    return vn


vanna = get_vanna_instance()
