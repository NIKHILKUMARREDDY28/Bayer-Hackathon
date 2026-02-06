# Use AWS Lambda Python base image (MANDATORY for Lambda)
FROM public.ecr.aws/lambda/python:3.12

# Copy AWS Lambda Web Adapter extension
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# Set working directory
WORKDIR /var/task

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv first
RUN pip install --no-cache-dir uv

# Install dependencies from lockfile
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Expose port used by web adapter
ENV PORT=8501

# Start Streamlit via Lambda Web Adapter
CMD ["uv", "run", "streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
