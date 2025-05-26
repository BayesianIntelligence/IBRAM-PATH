FROM python:3
# Make port 9487 available to the world outside this container
EXPOSE 9487
COPY requirements.txt /
RUN pip install -r /requirements.txt
#flask run from install file
COPY . /app
WORKDIR /app

RUN chmod 644 _server.py

CMD ["python", "_server.py"]