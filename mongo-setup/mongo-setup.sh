#!/usr/bin/env bash
set -e
HOST=mongodb            # Taken from docker-compose
DB=NOU_Enrollment       # Taken from config.py
MOUNT_PATH=/mongo-setup # Taken from docker-compose

seed_collection() {
  local collection="$1"
  local json_file_path="$2"
  echo "Setting up ${DB} db with ${collection} collection from ${json_file_path}..."
  mongoimport \
    --host "${HOST}" \
    --db "${DB}" \
    --collection "${collection}" \
    --type json \
    --file "${json_file_path}" \
    --jsonArray \
    --drop
  echo "Done setting ${collection} collection."
}

drop_collection() {
  local collection="$1"
  echo "Dropping stale ${collection} data..."

  mongosh --host "${HOST}" --eval "db.getSiblingDB('${DB}').${collection}.drop()"

  echo "Done dropping ${collection} collection."
}

seed_collection "user"   "${MOUNT_PATH}/users.json"
seed_collection "course" "${MOUNT_PATH}/courses.json"
drop_collection "enrollment"
