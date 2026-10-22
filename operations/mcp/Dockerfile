FROM python:3.13-slim@sha256:cf50a4f6ac4f026458b08d5222023d700ac806410dff5e9ca8728fa44f2b850f
RUN python -m pip uninstall --yes pip setuptools && python -c "import shutil,sysconfig; shutil.rmtree(sysconfig.get_path('stdlib')+'/ensurepip', ignore_errors=True)"
WORKDIR /mcp
COPY server.py /mcp/server.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
# Each authorized stdio session starts server.py through Kubernetes exec.
CMD ["python", "-c", "import time; time.sleep(2147483647)"]
