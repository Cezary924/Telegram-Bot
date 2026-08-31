import telebot
from dataclasses import dataclass, field

from core.config import Config
from core.db.storage import Storage
from core.i18n import Catalog
from core.registry import Registry
from core.version import Version


@dataclass
class Services:
    config: Config
    catalog: Catalog
    storage: Storage
    registry: Registry
    bot: telebot.TeleBot | None = None
    version: Version = field(default_factory=Version)
