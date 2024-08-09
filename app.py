from typing import Union
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
import os
import shutil

from fastapi import Depends, HTTPException, Security
import jwt
from datetime import datetime, timedelta
from typing import Dict


app = FastAPI()

# Replace with your MongoDB connection string
MONGO_CONNECTION_STRING = "mongodb+srv://jayanta:hCfi99jE8WfCaV35@test.o6u7v.mongodb.net"
DB_NAME = "Tour_Capture_3D"
COLLECTION_NAME = "media"



security = HTTPBearer()

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_CONNECTION_STRING)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]


@app.get("/")
def read_root():
    return {"Hello": "World"}




# These should be kept secret and possibly stored in environment variables
SECRET_KEY = "jayanta*123"
ALGORITHM = "HS256"


def decode_jwt(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if decoded_token["exp"] < datetime.timestamp(datetime.now()):
            raise jwt.ExpiredSignatureError("Token has expired")
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Could not validate credentials: {str(e)}")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    return decode_jwt(credentials.credentials)


@app.post("/token")
async def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)  # Default to 1 hour expiration
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/upload-tour")
async def upload_tour(file: UploadFile = File(...), token: str = Depends(verify_token)):
    try:
        # Create a temporary file to store the uploaded zip
        with open(f"{file.filename}", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Save file info to MongoDB
        document = {
            "filename": file.filename,
            "status": "unprocessed",
            "path": os.path.abspath(file.filename)
        }
        result = await collection.insert_one(document)
        
        return {"message": "Tour uploaded successfully", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file
        os.remove(file.filename)
