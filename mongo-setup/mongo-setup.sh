#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-mongodb}"          # Default for local docker-compose
DB="${DB:-NOU_Enrollment}"
MOUNT_PATH="${MOUNT_PATH:-/mongo-setup}"

seed_collection() {
  local collection="$1"
  local json_file_path="$2"
  echo "Setting up ${DB} db with ${collection} collection from ${json_file_path}..."
  if [[ -n "${MONGO_URI:-}" ]]; then
    mongoimport \
      --uri "${MONGO_URI}" \
      --collection "${collection}" \
      --type json \
      --file "${json_file_path}" \
      --jsonArray \
      --drop
  else
    mongoimport \
      --host "${HOST}" \
      --db "${DB}" \
      --collection "${collection}" \
      --type json \
      --file "${json_file_path}" \
      --jsonArray \
      --drop
  fi
  echo "Done setting ${collection} collection."
}

drop_collection() {
  local collection="$1"
  echo "Dropping stale ${collection} data..."
  if [[ -n "${MONGO_URI:-}" ]]; then
    mongosh "${MONGO_URI}" --eval "db.${collection}.drop()"
  else
    mongosh --host "${HOST}" --eval "db.getSiblingDB('${DB}').${collection}.drop()"
  fi
  echo "Done dropping ${collection} collection."
}

seed_collection "user"   "${MOUNT_PATH}/users.json"
seed_collection "course" "${MOUNT_PATH}/courses.json"
drop_collection "enrollment"
