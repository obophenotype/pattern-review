FROM python:3.5.2
USER root

ENV gh_user=''
ENV gh_password=''

WORKDIR /app

ADD ./requirements.txt /app/requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

ADD assets /app/assets
ADD ./app.py /app/app.py
ADD ./Procfile /app/Procfile

EXPOSE 80

ENV NAME patterns

CMD ["python", "app.py"]