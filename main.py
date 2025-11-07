from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
from email.header import Header
from email.mime.image import MIMEImage
import os
from dotenv import load_dotenv
import tempfile
from fastapi.responses import JSONResponse
import matplotlib.pyplot as plt
import io
import base64
import contextlib
import requests

load_dotenv()

app = FastAPI()

# Datos del correo
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
USERNAME = os.getenv("USERNAME")
 


class ImageRequest(BaseModel):
    filename: str
    image_base64: str
    email_reciever: str 
    subject: str


@app.post("/send-image/")
async def send_image(data: ImageRequest):
    try:
        # Decodificar imagen base64
        response = requests.get(data.image_base64)
        response.raise_for_status()
        image_data = response.content  # bytes
        email_reciever = data.email_reciever
        subject = data.subject

        # Guardar temporalmente la imagen
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name

        # Crear mensaje
        msg = MIMEMultipart()
        msg["From"] = formataddr((str(Header("FastAPI Service", "utf-8")), EMAIL_SENDER))
        msg["To"] = email_reciever
        msg["Subject"] = subject

        body = MIMEText("Se adjunta el gráfico por la API.", "plain")
        msg.attach(body)

        # Adjuntar imagen
        with open(tmp_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=data.filename)
        part["Content-Disposition"] = f'attachment; filename="{data.filename}"'
        msg.attach(part)

        # Enviar correo
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)

        return {"status": "success", "message": "Correo enviado correctamente"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Limpiar archivo temporal
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# Función auxiliar para subir la imagen
def subir_a_imgbb(image_base64: str) -> str:
    """Sube una imagen base64 a ImgBB y devuelve la URL pública."""
    response = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_API_KEY, "image": image_base64}
    )
    response.raise_for_status()
    return response.json()["data"]["url"]

# Modelo de entrada
class CodeRequest(BaseModel):
    code: str
plt.show = lambda *args, **kwargs: None

@app.post("/run-plot/")
async def run_plot(req: CodeRequest):
    """
    Recibe código Python que genera un gráfico con matplotlib/seaborn
    y devuelve la URL pública de la imagen subida a ImgBB.
    """
    try:
        # 1️⃣ Limpiar figuras previas
        plt.close("all")

        # 2️⃣ Desactivar plt.show() para que no abra ventanas
        plt.show = lambda *args, **kwargs: None

        # 3️⃣ Ejecutar el código del gráfico
        exec(req.code, {})

        # 4️⃣ Guardar figura en memoria
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()

        # 5️⃣ Subir a ImgBB y obtener URL pública
        image_url = subir_a_imgbb(img_base64)

        # 6️⃣ Devolver la URL
        return JSONResponse(content={"image_url": image_url})

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
