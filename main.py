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


@app.get('/')
def read_root() -> dict:
    """
    The read_root function returns a dictionary with the key 'message' and value of `WELCOME`

    :return: A dictionary with the key 'message' and the value of `welcome`
    :doc-author: Trelent
    """
    return {'message': messages.WELCOME}


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


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)

# http://0.0.0.0:8000/static/index.html
