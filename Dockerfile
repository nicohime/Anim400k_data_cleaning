FROM python:3.9


WORKDIR /code


COPY ./ /code


RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


CMD ["fastapi", "run", "main.py", "--port", "80"]