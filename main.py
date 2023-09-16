import pathlib
from typing import List

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from PyPDF2 import PdfReader
import uvicorn

from src.conf import messages
# from src.routes import notes

# locate templates  # Integrating our templates with the engine.
templates = Jinja2Templates(directory="templates")


def get_txt_from_pdf(file: str) -> str:
    # creating a pdf reader object
    reader = PdfReader(file)
    text = ''

    for page in range(len(reader.pages)):
        text += reader.pages[page].extract_text()

    return text



app = FastAPI()


# app.include_router(notes.router, prefix='/api')
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/templates', StaticFiles(directory='templates'), name='templates')


# ----- CHAT -----------------------------------

# returning home and chat templates
@app.get("/")
def get_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/chat")
def get_chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

"""
register and user endpoint does:
    Get user name from the frontend and validate (and parse) it with custom RegisterValidator pydantic model.
    Create a cookie on the browser with httponly set to True so that no script gets hold of it.
    Get user by reading browser cookie.
"""
@app.get("/api/current_user")
def get_user(request: Request):
    return request.cookies.get("X-Authorization")

class RegisterValidator(BaseModel):
    username: str

    class Config:
        orm_mode = True

@app.post("/api/register")
def register_user(user: RegisterValidator, response: Response):
    response.set_cookie(key="X-Authorization", value=user.username, httponly=True)
    # return True ## 

# manager
class SocketManager:
    """
    SocketManager does:
    Connect users to websocket with the help of connect function.
    Disconnect/Remove users with disconnect function.
    Send messages to all the connected users with broadcast function.
    """
    def __init__(self):
        self.active_connections: List[(WebSocket, str)] = []

    async def connect(self, websocket: WebSocket, user: str):
        await websocket.accept()
        self.active_connections.append((websocket, user))

    def disconnect(self, websocket: WebSocket, user: str):
        self.active_connections.remove((websocket, user))

    async def broadcast(self, data):
        for connection in self.active_connections:
            await connection[0].send_json(data)    

manager = SocketManager()

@app.websocket("/api/chat")
async def chat(websocket: WebSocket):
    """
    websocket chat function does:
    Check to see if user is registered/authenticated by reading from browser cookie which we are going to set next.
    Connect user to websocket with connect() function of SocketManager.
    Get data from connected user and broadcast it to all connected users with websocket.receive_json() and broadcast() respectively.
    """
    sender = websocket.cookies.get("X-Authorization")
    if sender:
        await manager.connect(websocket, sender)
        response = {
            "sender": sender,
            "message": "got connected"
        }
        await manager.broadcast(response)
        try:
            while True:
                data = await websocket.receive_json()
                await manager.broadcast(data)
        except WebSocketDisconnect:
            manager.disconnect(websocket, sender)
            response['message'] = "left"
            await manager.broadcast(response)

# ----- alternative simplest CHAT --ok------------------------


class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)



    async def broadcast(self, data: str):
        for connection in self.connections:
            await connection.send_text(data)


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    while True:
        data = await websocket.receive_text()
        await manager.broadcast(f"Client {client_id}: {data}")
        

# ----- UPLOAD FILE -----------------------------------
@app.post('/uploadfile/')
async def create_upload_file(file: UploadFile = File()) -> dict:
    pathlib.Path('uploads').mkdir(exist_ok=True)
    file_path = f'uploads/{file.filename}'

    file_type = file.filename.split('.')[-1].lower()
    if file_type == 'pdf':
        with open(file_path, 'wb') as f:
            f.write(await file.read())

        text = get_txt_from_pdf(file_path) # 'example.pdf'
        print(text)

        return {'file_text': text}  # file_path
    
    else:
        return {'file_text': f'Incorrect file-type. {file_type} not a PDF.'}  # file_path

# ----- root 0 -----------------------------------
# @app.get('/')
# def read_root() -> dict:
#     """
#     The read_root function returns a dictionary with the key 'message' and value of `WELCOME`

#     :return: A dictionary with the key 'message' and the value of `welcome`
#     :doc-author: Trelent
#     """
#     return {'message': messages.WELCOME}


# ----- from example -----------------------------------
class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

@app.post("/items")
async def create_item(item: Item):
    return item

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    return {"item_id": item_id, "item": item}

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    return {"item_id": item_id}

# ----- RUN -----------------------------------

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)

# http://0.0.0.0:8000/docs
# http://0.0.0.0:8000/static/index.html

# ok:
# http://0.0.0.0:8000/static/chat.html

# something wrong:
# http://0.0.0.0:8000/
# http://0.0.0.0:8000/api/register
# http://0.0.0.0:8000/chat/
# http://0.0.0.0:8000/api/current_user
