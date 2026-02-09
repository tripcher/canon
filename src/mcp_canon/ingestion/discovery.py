"""Discovery module for scanning library directory."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiscoveredGuide:
    """Represents a discovered guide in the library."""

    namespace: str
    guide_name: str
    index_path: Path
    guide_path: Path | None  # GUIDE.md if exists
    references_dir: Path | None  # references/ if exists
    assets_dir: Path | None  # assets/ if exists

    @property
    def id(self) -> str:
        """Return guide ID in format 'namespace/guide_name'."""
        return f"{self.namespace}/{self.guide_name}"


def discover_guides(library_path: Path) -> list[DiscoveredGuide]:
    """
    Scan library directory for INDEX.md files.

    Expected structure:
        ./library/<namespace>/<guide_name>/INDEX.md

    Args:
        library_path: Path to the library root directory

    Returns:
        List of discovered guides with their paths
    """
    guides: list[DiscoveredGuide] = []

    if not library_path.exists():
        return guides

    # Iterate over namespace directories (L1)
    for tech_dir in library_path.iterdir():
        if not tech_dir.is_dir() or tech_dir.name.startswith("."):
            continue

        namespace = tech_dir.name

        # Iterate over guide directories (L2)
        for guide_dir in tech_dir.iterdir():
            if not guide_dir.is_dir() or guide_dir.name.startswith("."):
                continue

            guide_name = guide_dir.name
            index_path = guide_dir / "INDEX.md"

            # Skip if no INDEX.md
            if not index_path.exists():
                continue

            # Check for optional files/directories
            guide_path = guide_dir / "GUIDE.md"
            references_dir = guide_dir / "references"
            assets_dir = guide_dir / "assets"

            guides.append(
                DiscoveredGuide(
                    namespace=namespace,
                    guide_name=guide_name,
                    index_path=index_path,
                    guide_path=guide_path if guide_path.exists() else None,
                    references_dir=references_dir if references_dir.is_dir() else None,
                    assets_dir=assets_dir if assets_dir.is_dir() else None,
                )
            )

    return guides


def discover_index_files(library_path: Path) -> list[Path]:
    """
    Simple discovery that returns just INDEX.md paths.

    Args:
        library_path: Path to the library root directory

    Returns:
        List of paths to INDEX.md files
    """
    return [guide.index_path for guide in discover_guides(library_path)]
