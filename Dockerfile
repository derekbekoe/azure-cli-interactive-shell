FROM python:3.6

WORKDIR azclishell
COPY . /azclishell

RUN pip install az-cli-shell

RUN az-cli

WORKDIR /

CMD bash