FROM python:3.5.2
USER root

ENV gh_user=''
ENV gh_password=''
ENV curators_csv=http://purl.obolibrary.org/obo/upheno/src/patterns/curators.csv
ENV issues_csv=http://purl.obolibrary.org/obo/upheno/src/patterns/pattern_issues.csv
ENV pattern_dir=http://purl.obolibrary.org/obo/upheno/src/patterns/
ENV new_ticket_url=https://github.com/obophenotype/upheno/issues/new
ENV repo_name=obophenotype/upheno
ENV pattern_iri_prefix=http://purl.obolibrary.org/obo/upheno/patterns/

WORKDIR /app

ADD ./requirements.txt /app/requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

ADD assets /app/assets
ADD ./app.py /app/app.py
ADD ./Procfile /app/Procfile

EXPOSE 80

ENV NAME patterns

CMD ["python", "-u","app.py"]