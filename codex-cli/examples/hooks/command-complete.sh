#!/bin/bash

# Example onCommandComplete hook script
# This script is executed after each command completes

echo "✅ Command completed: $CODEX_COMMAND"
echo "Exit code: $CODEX_EXIT_CODE"
echo "Working directory: $CODEX_WORKING_DIR"
echo "Timestamp: $(date)"

# Read event data from stdin
EVENT_DATA=$(cat)

# Extract command details
COMMAND=$(echo "$EVENT_DATA" | jq -r '.command | join(" ")' 2>/dev/null || echo "$CODEX_COMMAND")
EXIT_CODE=$(echo "$EVENT_DATA" | jq -r '.exitCode // 0' 2>/dev/null || echo "$CODEX_EXIT_CODE")
DURATION=$(echo "$EVENT_DATA" | jq -r '.durationMs // 0' 2>/dev/null || echo "0")
SUCCESS=$(echo "$EVENT_DATA" | jq -r '.success // false' 2>/dev/null)

# Log command completion
if [ "$SUCCESS" = "true" ] || [ "$EXIT_CODE" = "0" ]; then
    echo "$(date): SUCCESS: '$COMMAND' completed in ${DURATION}ms" >> ~/.codex/command-log.txt
else
    echo "$(date): FAILED: '$COMMAND' failed with exit code $EXIT_CODE" >> ~/.codex/command-log.txt
fi

# Example: Handle test command results
if [[ "$COMMAND" =~ (npm\ test|pytest|cargo\ test|go\ test) ]]; then
    if [ "$SUCCESS" = "true" ] || [ "$EXIT_CODE" = "0" ]; then
        echo "🎉 Tests passed!"
        
        # Uncomment to send success notification
        # curl -X POST "$SLACK_WEBHOOK_URL" \
        #   -H 'Content-Type: application/json' \
        #   -d "{\"text\":\"✅ Tests passed in $(pwd)\"}"
    else
        echo "❌ Tests failed with exit code $EXIT_CODE"
        
        # Uncomment to send failure notification
        # curl -X POST "$SLACK_WEBHOOK_URL" \
        #   -H 'Content-Type: application/json' \
        #   -d "{\"text\":\"❌ Tests failed in $(pwd) (exit code: $EXIT_CODE)\"}"
    fi
fi

# Example: Handle build command results
if [[ "$COMMAND" =~ (npm\ run\ build|cargo\ build|go\ build|make) ]]; then
    if [ "$SUCCESS" = "true" ] || [ "$EXIT_CODE" = "0" ]; then
        echo "🔨 Build successful!"
        
        # Example: Tag successful builds
        if git rev-parse --git-dir > /dev/null 2>&1; then
            BUILD_TAG="build-success-$(date +%Y%m%d-%H%M%S)"
            git tag "$BUILD_TAG" 2>/dev/null || true
            echo "Tagged build: $BUILD_TAG"
        fi
    else
        echo "💥 Build failed with exit code $EXIT_CODE"
    fi
fi

# Example: Handle deployment command results
if [[ "$COMMAND" =~ ^(docker|kubectl|helm|npm\ run\ deploy) ]]; then
    if [ "$SUCCESS" = "true" ] || [ "$EXIT_CODE" = "0" ]; then
        echo "🚀 Deployment successful!"
        
        # Uncomment to send deployment success notification
        # curl -X POST "$SLACK_WEBHOOK_URL" \
        #   -H 'Content-Type: application/json' \
        #   -d "{\"text\":\"🚀 Deployment completed successfully in $(pwd)\"}"
    else
        echo "💥 Deployment failed with exit code $EXIT_CODE"
        
        # Uncomment to send deployment failure notification
        # curl -X POST "$SLACK_WEBHOOK_URL" \
        #   -H 'Content-Type: application/json' \
        #   -d "{\"text\":\"💥 Deployment failed in $(pwd) (exit code: $EXIT_CODE)\"}"
    fi
fi

exit 0
