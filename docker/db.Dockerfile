# syntax=docker/dockerfile:1.3
ARG POSTGRES_TAG=11

FROM postgres:${POSTGRES_TAG}

COPY . /
