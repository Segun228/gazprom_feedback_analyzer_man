FROM apache/superset:latest

USER root

RUN pip install sqlalchemy-clickhouse infi-clickhouse-orm clickhouse-connect clickhouse-sqlalchemy

USER superset