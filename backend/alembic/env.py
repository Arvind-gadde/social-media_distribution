from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.session import Base

# Register ALL models with Base.metadata for migration auto-generation
from app.models.models import User  # noqa: F401
from app.domains.control.models import (  # noqa: F401
    Workspace, WorkspaceMembership, Niche, WorkspaceNiche,
    SocialAccount, AuditLog, UsageMeter,
    BudgetPolicy, OutboxEvent, WebhookReceipt,
)
from app.domains.intelligence.models import (  # noqa: F401
    SourceRegistry, SourceDocument, SourceDocumentInsight,
    WorkspaceInsight, Trend, CompetitorProfile, CompetitorObservation,
    AgentRun, AgentStep,
    PromptCatalog, PromptVersion, ProviderPolicy,
    AgentConfig, AgentInsight,
)
from app.domains.execution.models import (  # noqa: F401
    ContentProject, ContentVariant, ContentAsset,
    PublishJob, PublishAttempt, CreatorGoal, GoalCheckIn,
    ApprovalRequest, Notification, AnalyticsFact,
    MediaEdit,
)
from app.domains.business.models import (  # noqa: F401
    DMInbox, Collaboration, ContractDraft,
)
from app.domains.notifications.models import (  # noqa: F401
    DeviceToken,
)

from app.config import get_settings

settings = get_settings()
config = context.config
config.set_main_option("sqlalchemy.url", settings.sync_database_url)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
