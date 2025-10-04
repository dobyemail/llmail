from dataclasses import dataclass
from typing import Optional

from llmass.logging_utils import LogCtl


@dataclass
class OrganizerConfig:
    email: str
    password: str
    server: Optional[str] = None
    limit: Optional[int] = None
    since_days: Optional[int] = None
    since_date: Optional[str] = None
    folder: Optional[str] = None
    include_subfolders: bool = False
    similarity_threshold: Optional[float] = None
    min_cluster_size: Optional[int] = None
    min_cluster_fraction: Optional[float] = None
    dry_run: bool = False
    verbose: bool = False


class OrganizerApp:
    def __init__(self, log: Optional[LogCtl] = None):
        self.log = log or LogCtl(verbose=False)

    def run(self, cfg: OrganizerConfig) -> None:
        # For now, delegate to legacy EmailOrganizer to stay functional.
        from email_organizer import EmailOrganizer

        bot = EmailOrganizer(
            cfg.email,
            cfg.password,
            cfg.server,
            similarity_threshold=cfg.similarity_threshold,
            min_cluster_size=cfg.min_cluster_size,
            min_cluster_fraction=cfg.min_cluster_fraction,
            dry_run=cfg.dry_run,
            verbose=cfg.verbose,
        )
        if bot.connect():
            try:
                bot.organize_mailbox(
                    limit=cfg.limit if cfg.limit is not None else 100,
                    since_days=cfg.since_days if cfg.since_days is not None else 7,
                    since_date=cfg.since_date,
                    folder=cfg.folder,
                    include_subfolders=cfg.include_subfolders,
                )
            finally:
                bot.disconnect()


def run_clean_from_args(args) -> None:
    log = LogCtl(verbose=bool(getattr(args, 'verbose', False)))
    cfg = OrganizerConfig(
        email=getattr(args, 'email', None) or '',
        password=getattr(args, 'password', None) or '',
        server=getattr(args, 'server', None),
        limit=getattr(args, 'limit', None),
        since_days=getattr(args, 'since_days', None),
        since_date=getattr(args, 'since_date', None),
        folder=getattr(args, 'folder', None),
        include_subfolders=bool(getattr(args, 'include_subfolders', False)),
        similarity_threshold=getattr(args, 'similarity_threshold', None),
        min_cluster_size=getattr(args, 'min_cluster_size', None),
        min_cluster_fraction=getattr(args, 'min_cluster_fraction', None),
        dry_run=bool(getattr(args, 'dry_run', False)),
        verbose=bool(getattr(args, 'verbose', False)),
    )
    if not cfg.email or not cfg.password:
        log.error("❌ Brak wymaganych danych logowania. Użyj --email i --password lub .env")
        return
    OrganizerApp(log).run(cfg)
