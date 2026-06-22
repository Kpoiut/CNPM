"""Import all model modules exactly once so SQLAlchemy metadata is complete."""


def load_all_models() -> None:
    # Imports are intentionally local: database configuration remains cheap for
    # commands that only need an engine, while migrations can register all tables.
    from src.backend import models  # noqa: F401
    from src.backend.auth import models as auth_models  # noqa: F401
    from src.backend.community import models as community_models  # noqa: F401
