from peewee import *
from datetime import datetime
import logging
from playhouse.sqlite_ext import SqliteExtDatabase

logger = logging.getLogger(__name__)

db = SqliteExtDatabase('tasks.db', pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 64,
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 0,
    'timeout': 30
})


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    user_id = IntegerField(unique=True)
    username = CharField(null=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)
    last_activity = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'users'


class Task(BaseModel):
    user = ForeignKeyField(User, backref='tasks', on_delete='CASCADE')
    text = TextField()
    category = CharField()
    is_done = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now)
    completed_at = DateTimeField(null=True)

    class Meta:
        table_name = 'tasks'
        indexes = (
            (('user', 'is_done'), False),
            (('user', 'category'), False),
        )


def initialize_db():
    try:
        if not db.is_closed():
            db.close()

        db.connect(reuse_if_open=True)

        with db.atomic():
            db.create_tables([User, Task], safe=True)

        logger.info("База данных готова")
    except Exception as e:
        logger.critical(f"Ошибка БД: {e}", exc_info=True)
        raise


def get_db_connection():
    if db.is_closed():
        db.connect()
    return db