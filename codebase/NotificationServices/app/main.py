from fastapi import Depends, FastAPI, HTTPException
app:FastAPI = FastAPI()
@app.get('/')
async def root():
    return {"message": "Notification Management Service"}