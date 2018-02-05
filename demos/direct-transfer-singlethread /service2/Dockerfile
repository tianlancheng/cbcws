FROM python:2
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /home
mkdir data
COPY service2.py ./
ENTRYPOINT ["python","service2.py"]