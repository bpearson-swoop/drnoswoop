#!/bin/bash

CURRENT_DIR=$(dirname "$0")
. ${CURRENT_DIR}/.venv/bin/activate

if [ -f "${CURRENT_DIR}/.env" ]; then
    export $(cat ${CURRENT_DIR}/.env | xargs)
fi

export PYTHONWARNINGS="ignore:Unverified HTTPS request"

FILE="${1:-""}"
if [ "${FILE}" != "" ] && [ -f "${FILE}" ]; then
    python "${CURRENT_DIR}/${FILE}"
else
    streamlit run ${CURRENT_DIR}/chat.py
fi
