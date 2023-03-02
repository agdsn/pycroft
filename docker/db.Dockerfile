# syntax=docker/dockerfile:1.4
ARG POSTGRES_TAG=14

FROM docker.io/postgres:${POSTGRES_TAG}

COPY . /
