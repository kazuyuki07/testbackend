from fastapi import FastAPI
from uvicorn import run

from auth import router as auth_router
from users import router as users_router
from tasks import router as tasks_router

from admin import adminpanel


app = FastAPI()
adminpanel.mount_to(app)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tasks_router)

if __name__ == "__main__":
    run("main:app", host="0.0.0.0", port=8000, reload= True)