#!/bin/bash

find . -type f -name "*.sh" -exec chmod +x {} +
find . -type f -name "*.sh"

git add .
git commit -m 'Updated'
git pull --rebase
git push
