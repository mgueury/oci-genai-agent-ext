#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# Node (JET/Angular/ReactJS)
sudo dnf module enable -y nodejs:20
sudo dnf install -y nodejs

# Agent Chat UI
cd src
npx create-agent-chat-app -Y --project-name agent-chat-app --package-manager npm 
sed -i "s/next dev/next dev -p 8080/" agent-chat-app/apps/web/package.json

