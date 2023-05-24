FROM python:3.7-slim

RUN apt update
RUN apt install gcc -y

WORKDIR /app
COPY . .

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install -r requirements.txt

RUN chmod +x run.sh
RUN chmod +x run_abs.sh

COPY run_abs.sh /usr/local/bin/run_abs.sh

ENV PYTHONPATH=.
#CMD ["python", "hex_forest/run.py", "-t=http"]
CMD ["./run.sh"]
CMD /usr/local/bin/run_abs.sh
EXPOSE 8001