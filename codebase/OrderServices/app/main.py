from fastapi import Depends, FastAPI, HTTPException

app: FastAPI = FastAPI()


@app.get("/")
async def root():
    return {"message": "Order Management Service"}
