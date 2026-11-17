FROM python:3.13-slim

RUN mkdir -p /usr/app && \
	adduser --home /home/user --disabled-password --uid 1001 user && \
	chown -R user:user /usr/app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

USER user
WORKDIR /usr/app

COPY --chown=user:user src/ src/
COPY --chown=user:user custom-code/ custom-code/
COPY --chown=user:user \
	./pyproject.toml \
	./README.md \
	./mkdocs.yml \
	./uv.lock \
	./LICENSE .

ADD --chown=user:user https://astral.sh/uv/install.sh ./uv-installer.sh
RUN sh ./uv-installer.sh && rm ./uv-installer.sh

ENV PATH="/home/user/.local/bin/:$PATH"

RUN uv venv --no-python-downloads && \
	uv sync --no-dev --locked -n

EXPOSE ${PORT:-80}/tcp
ENTRYPOINT ["sh", "-c", "exec uv run streamdaq serve --clear --files /usr/app/custom-code/ --host 0.0.0.0 --port \"${PORT:-80}\" \"$@\"", "--"]
