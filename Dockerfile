# Usa la imagen oficial de Python (elige la versión que necesites)
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de dependencias (requirements.txt)
COPY requirements.txt .

# Instala las dependencias necesarias
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el código de la aplicación
COPY . .

# Expone el puerto 8080 (Cloud Run escucha en este puerto)
EXPOSE 8080

# Comando para ejecutar la aplicación (ajusta si usas otro comando)
CMD ["python", "app.py"]
