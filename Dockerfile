FROM rasa/rasa-pro:3.21.3

WORKDIR /app
COPY --chown=1001:0 . /app
RUN mkdir -p /app/models && chown 1001:0 /app/models
ENV SANIC_WORKERS=1
ENTRYPOINT []
CMD ["sh", "-c", "set -e; if [ ! -f models/community.tar.gz ]; then rasa train --fixed-model-name community; fi; exec rasa run --model models/community.tar.gz --credentials credentials.yml --endpoints endpoints.yml --enable-api --cors '*' --interface 0.0.0.0 --port 5005"]
