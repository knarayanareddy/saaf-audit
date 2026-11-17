#!/bin/bash
# deploy a signup
HANDLE="$1"
eval "gh api /users/$HANDLE --jq .id"
bash -c "echo adding ${HANDLE} >> /var/log/signups.log"
