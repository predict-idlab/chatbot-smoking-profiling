FROM ubuntu:20.04

RUN apt-get update -y && \
    apt-get install -y python3-pip python-dev

# copies files from the first parameter to the destination parameter
COPY requirements.txt /app/

# set the working directory (all following instructions operate within this directory)
WORKDIR /app/

RUN pip install -r requirements.txt

RUN python3 -m spacy download en_core_web_lg

COPY . /app/

EXPOSE 8000:8000

ENV PYTHONPATH=/app
ENV VERIFY_TOKEN="testchatbot"
ENV PAGE_ACCESS_TOKEN="EAALoAkPTKscBANEq0nTkDtYjE2reFL13rTyMtZCznuZCSYMi7ZAu8F7I1hVDeZBEbZAUzrWoA9G3n6We3DF8L5af3dfEg8D5HhKOxwGfM0QMgVuqHZBdadSaBJZAN3sP6lJUEjEwyLmdenmmJiRhhBjxH32v0xoZBqloYYebk9tjZAKggX0npIUT8"

CMD ["uvicorn", "App:app","--host", "0.0.0.0", "--port", "8000"]