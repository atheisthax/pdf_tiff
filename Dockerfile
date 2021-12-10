FROM python:3-slim

WORKDIR /opt/pdf_tiff

COPY . .
RUN apt-get update && apt-get install -y libmagickwand-dev ghostscript --no-install-recommends && \
    pip install --no-cache-dir -r requirements.txt

CMD [ "python", "main.py" ]
