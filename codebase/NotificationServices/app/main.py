import asyncio
from contextlib import asynccontextmanager
import logging
from fastapi import Depends, FastAPI, HTTPException
from app.consumer import main
from app.db import create_table


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#  It contains all the instructions that will run when the application will start
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_table()
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(main.start_consuming_user())
    task2 = loop.create_task(main.start_consuming_order())
    task3 = loop.create_task(main.start_consuming_payment())
    try:
        yield
    finally:
        for task in [task1,task2,task3]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
app:FastAPI = FastAPI(lifespan=lifespan )


@app.get("/")
async def read_root():
    return {"message": "Notification Management Service"}
