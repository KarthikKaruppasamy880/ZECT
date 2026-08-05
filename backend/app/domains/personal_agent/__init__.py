"""Personal Agent domain routers."""

from app.domains.personal_agent import memory
from app.domains.personal_agent import skills_engine
from app.domains.personal_agent import playbooks
from app.domains.personal_agent import scheduler
from app.domains.personal_agent import transfer
from app.domains.personal_agent import data_flywheel
from app.domains.personal_agent import data_layer
from app.domains.personal_agent import dream_engine
from app.domains.personal_agent import conversations
from app.domains.personal_agent import session_insights
from app.domains.personal_agent import persistent_sessions
from app.domains.personal_agent import user_sessions
from app.domains.personal_agent import file_organize

__all__ = ['memory', 'skills_engine', 'playbooks', 'scheduler', 'transfer', 'data_flywheel', 'data_layer', 'dream_engine', 'conversations', 'session_insights', 'persistent_sessions', 'user_sessions', 'file_organize']
