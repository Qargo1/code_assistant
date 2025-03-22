from sqlalchemy import Column, String, JSON, Enum, Text, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class SemanticType(enum.Enum):
    DATA = "data"
    API = "api"
    UI = "ui"
    CORE = "core"
    UTIL = "util"

class PatternType(enum.Enum):
    AUTH = "auth"
    DB_QUERY = "db_query"
    EVENT = "event"

class FileMetadata(Base):
    __tablename__ = 'file_metadata'
    
    file_path = Column(String(500), primary_key=True)
    semantic_type = Column(Enum(SemanticType))
    dependencies = Column(JSON)
    key_functions = Column(JSON)  # Храним как массив строк
    last_analyzed = Column(TIMESTAMP)

class CodePatterns(Base):
    __tablename__ = 'code_patterns'
    
    id = Column(String(100), primary_key=True)
    pattern_type = Column(Enum(PatternType))
    implementation = Column(Text)
    file_references = Column(JSON)