FROM golang:rc-alpine
RUN apk add --no-cache git
RUN apk add --no-cache gcc
RUN apk add --no-cache musl-dev
RUN git clone "https://github.com/mailslurper/mailslurper/" /opt/mailslurper
WORKDIR /opt/mailslurper/cmd/mailslurper
RUN go get github.com/mjibson/esc
RUN cd /opt/mailslurper/cmd/mailslurper
COPY ./mailslurper.conf config.json
RUN go get
RUN go generate
RUN go build
ENTRYPOINT ["/opt/mailslurper/cmd/mailslurper/mailslurper"]
