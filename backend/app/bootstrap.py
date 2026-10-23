"""Initialize schema and public product cards before the Render API starts."""
import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings
from app.seed import seed


def main() -> None:
    # Validate the production configuration before connecting or changing data.
    get_settings()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    # Idempotent insert-only seed: no existing cards, accounts or texts overwritten.
    asyncio.run(seed(None))


if __name__ == "__main__":
    main()
