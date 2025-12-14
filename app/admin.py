from starlette_admin.contrib.sqla import Admin, ModelView
from sqlalchemy import create_engine

from database import DATABASE_URL
from models import User, Task, Comment

adminpanel = Admin(create_engine(DATABASE_URL, connect_args={"check_same_thread": False}))

adminpanel.add_view(ModelView(User, icon="User"))
adminpanel.add_view(ModelView(Task, icon="Task"))
adminpanel.add_view(ModelView(Comment, icon="Comment"))