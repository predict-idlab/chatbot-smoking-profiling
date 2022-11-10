FROM ubuntu:20.04

RUN apt-get update -y && \
    apt-get install -y python3-pip python-dev

# copies files from the first parameter to the destination parameter
COPY app/requirements.txt /trigger/

# set the working directory (all following instructions operate within this directory)
WORKDIR /trigger/

RUN pip install -r requirements.txt

RUN python3 -m spacy download en_core_web_lg

COPY app /trigger/

ENV PYTHONPATH=/trigger

CMD ["python3", "update.py"]