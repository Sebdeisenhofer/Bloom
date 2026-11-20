FROM rasa/rasa-pro:3.21.3

WORKDIR /app
COPY --chown=1001:0 . /app
RUN mkdir -p /app/models && chown 1001:0 /app/models
ENV SANIC_WORKERS=1
ENTRYPOINT []
# Train on first start, and retrain automatically whenever the conversation files change
# (so `docker compose up --build` is always the only command needed).
# With OPENAI_API_KEY in .env the chat uses your OpenAI account (endpoints-openai.yml) instead of Rasa's shared endpoint.
CMD ["sh", "-c", "set -e; H=$(cat config.yml domain.yml endpoints.yml data/*.yml | sha256sum | cut -c1-16); if [ ! -f models/community.tar.gz ] || [ \"$(cat models/.trained-from 2>/dev/null)\" != \"$H\" ]; then rasa train --fixed-model-name community && echo $H > models/.trained-from; fi; E=endpoints.yml; if [ -n \"$OPENAI_API_KEY\" ]; then E=endpoints-openai.yml; echo 'Using your OpenAI key for the chat'; fi; exec rasa run --model models/community.tar.gz --credentials credentials.yml --endpoints $E --enable-api --cors '*' --interface 0.0.0.0 --port 5005"]
