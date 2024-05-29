# Dockerfile
FROM python:3.11-slim-bullseye

WORKDIR /opt/image_search_tools

# make sure all messages always reach console
ENV PYTHONUNBUFFERED=1

ENV PATH "$PATH:/root/.local/bin/"

#copying the project files
COPY . /opt/image_search_tools

# installing dependencies
RUN pip install -r requirements.txt

# run job
CMD python import_index_pipeline.py
