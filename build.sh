#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Pillow's build dependencies
apt-get update
apt-get install -y libjpeg-dev zlib1g-dev
