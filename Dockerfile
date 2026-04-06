FROM python:3.14.0

WORKDIR /aqi-app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . . 

COPY models ./models

EXPOSE 3000

RUN chmod -R 777 /aqi-app/instance/

CMD ["python" , "app.py"]

