FROM node:24 AS builder

WORKDIR /web

RUN --mount=type=cache,target=/root/.npm \
    --mount=type=bind,source=web/package.json,target=package.json \
    --mount=type=bind,source=web/package-lock.json,target=package-lock.json \
    npm ci

# Copy the source code into the container and compile TypeScript.
COPY web/ .
RUN npm run build


# Runner stage: minimal runtime image with compiled app and production deps.
FROM python:3.14 AS runner
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --locked
COPY server/ .

COPY --from=builder --chown=node:node /web/dist ./static

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
ENV PATH="/app/.venv/bin:$PATH"
CMD [ "fastapi", "run", "main.py" ]