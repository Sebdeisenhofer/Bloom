FROM rasa/rasa-sdk:3.21.2

WORKDIR /app
COPY actions/ /app/actions/
ENV COMMUNITY_DB_PATH=/data/community.sqlite3
USER root
RUN mkdir -p /data && chown -R 1001:0 /data
USER 1001
CMD ["start", "--actions", "actions", "--port", "5055"]
