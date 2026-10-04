# Local recipe. Pin PYTHON_IMAGE to an approved digest for a release build.
ARG PYTHON_IMAGE=python:3.11-slim-bookworm
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
# Install the exact prebuilt wheel selected by the operator; never an editable checkout.
ARG WHEEL=dist/humanwill_policies-0.2.0b1-py3-none-any.whl
COPY ${WHEEL} /app/wheels/
RUN python -m pip install --no-cache-dir -r /app/requirements.txt \
    && python -m pip install --no-cache-dir --no-deps /app/wheels/*.whl \
    && python -m pip check \
    && rm -r /app/wheels
USER 65532:65532
EXPOSE 8088
ENTRYPOINT ["humanwill-policies"]
CMD ["--help"]
