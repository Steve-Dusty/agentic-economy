#!/bin/bash

VOLUME_NAME=$1
ENCRYPTION_KEY=$2

if [ -z "$VOLUME_NAME" ] || [ -z "$ENCRYPTION_KEY" ]; then
    echo "Usage: $0 <volume_name> <encryption_key>"
    exit 1
fi

if ! command -v cryptsetup &> /dev/null; then
    echo "cryptsetup not found. Installing..."
    apt-get update && apt-get install -y cryptsetup
fi

echo "Creating encrypted volume: $VOLUME_NAME"
echo "$ENCRYPTION_KEY" | cryptsetup luksFormat /dev/mapper/$VOLUME_NAME
echo "$ENCRYPTION_KEY" | cryptsetup luksOpen /dev/mapper/$VOLUME_NAME $VOLUME_NAME

echo "Volume $VOLUME_NAME encrypted and ready"

