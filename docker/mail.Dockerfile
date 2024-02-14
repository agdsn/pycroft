FROM debian:unstable

RUN apt-get update && apt-get install -y python3 python3-aiosmtpd python3-termcolor

WORKDIR /opt/mail
COPY mail.py mail.py

ENTRYPOINT ["python3", "mail.py"]
