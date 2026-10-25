"""company-ai-agents: a company org chart of AI agent definitions.

Public API:
    load_catalog(root)      -> Catalog (roles, departments, graph)
    validate(root)          -> list[str] of problems (empty when clean)
    compose(catalog, answers) -> Team
    export_team(catalog, team, target, out_dir) -> list[Path]
"""

from .catalog import Catalog, Role, load_catalog
from .compose import Team, compose
from .export import export_team
from .finder import find
from .solve import solve, write_outputs
from .validate import validate

__all__ = ["Catalog", "Role", "Team", "compose", "export_team", "find", "load_catalog", "solve", "validate", "write_outputs"]
__version__ = "0.1.0"
