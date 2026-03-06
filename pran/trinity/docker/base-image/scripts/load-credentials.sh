#!/bin/bash

if [ -f "/config/credentials.json" ]; then
    echo "Loading credentials from /config/credentials.json"
    
    export CREDENTIALS_LOADED=true
    
    for mcp_server in $(jq -r 'keys[]' /config/credentials.json); do
        server_upper=$(echo "$mcp_server" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
        
        if jq -e ".[\"$mcp_server\"].api_key" /config/credentials.json > /dev/null 2>&1; then
            api_key=$(jq -r ".[\"$mcp_server\"].api_key" /config/credentials.json)
            export "${server_upper}_API_KEY=$api_key"
            echo "Loaded ${server_upper}_API_KEY"
        fi
        
        if jq -e ".[\"$mcp_server\"].token" /config/credentials.json > /dev/null 2>&1; then
            token=$(jq -r ".[\"$mcp_server\"].token" /config/credentials.json)
            export "${server_upper}_TOKEN=$token"
            echo "Loaded ${server_upper}_TOKEN"
        fi
        
        if jq -e ".[\"$mcp_server\"].access_token" /config/credentials.json > /dev/null 2>&1; then
            access_token=$(jq -r ".[\"$mcp_server\"].access_token" /config/credentials.json)
            export "${server_upper}_ACCESS_TOKEN=$access_token"
            echo "Loaded ${server_upper}_ACCESS_TOKEN"
        fi
    done
    
    echo "Credentials loaded successfully"
else
    echo "No credentials file found at /config/credentials.json"
    echo "Agent will run without credentials"
fi

