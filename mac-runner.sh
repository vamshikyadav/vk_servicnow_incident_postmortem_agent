# Create a new user (replace 'github-runner' with your preferred username)
sudo dscl . -create /Users/github-runner
sudo dscl . -create /Users/github-runner UserShell /bin/bash
sudo dscl . -create /Users/github-runner RealName "GitHub Runner"
sudo dscl . -create /Users/github-runner UniqueID 502
sudo dscl . -create /Users/github-runner PrimaryGroupID 20
sudo dscl . -create /Users/github-runner NFSHomeDirectory /Users/github-runner

# Set a password
sudo passwd github-runner

# Create the home directory
sudo createhomedir -c -u github-runner

sudo dscl . -append /Groups/admin GroupMembership github-runner

sudo -u github-runner -i
# or
su - github-runner

# Create a directory for the runner
mkdir actions-runner && cd actions-runner

# Download the latest runner (check https://github.com/actions/runner/releases for latest version)
curl -o actions-runner-osx-arm64.tar.gz -L https://github.com/actions/runner/releases/download/v2.323.0/actions-runner-osx-arm64-2.323.0.tar.gz

# Extract
tar xzf ./actions-runner-osx-arm64.tar.gz

# Configure the runner (get the token from GitHub → Repo → Settings → Actions → Runners → New self-hosted runner)
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# Install as a launchd service (so it auto-starts)
./svc.sh install
./svc.sh start

# Check status
./svc.sh status

./svc.sh stop      # Stop the runner
./svc.sh start     # Start the runner
./svc.sh status    # Check status
./svc.sh uninstall # Remove the service