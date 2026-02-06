# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Copy AWS Lambda Web Adapter
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV PORT=8501

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies
# --frozen ensures we stick to the lockfile
# --no-install-project means we don't install the current package itself (yet), just dependencies
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application
COPY . .

# Run the application
# We use `uv run` to ensure it uses the virtual environment created by uv
ENTRYPOINT ["uv", "run", "streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
