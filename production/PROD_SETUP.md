# Overview
This is how I currently setup my production server that runs infinitd.rofer.me.

It uses a podman container automatically (re)started by a user systemd instance
so it doesn't require root permissions.

# systemd setup
1. Enable per-user systemd to startup at login with: loginctl enable-linger <username>
2. Copy infinitd-backend.service to ~/.config/systemd/user/
3. Reload systemd files: systemctl --user daemon-reload
4. Enable it so it starts automatically: systemctl --user --enable infinitd-backend.service

# Repo setup
1. Make a bare clone of the repo named infinitd-backend.git
2. Copy post-receive to infinitd-backend.git/hooks/
3. Mark it as executable: chmod a+x infinitd-backend.git/hooks/post-receive

# Initial container setup
1. Create a volume to store the game data: podman volume create backend-data
2. Create a container to setup initial data: podman container create --name temp --mount type=volume,source=backend-data,target=/InfiniTDServer/data hello-world
3. Copy your private Firebase key to the container: podman cp ./privateFirebaseKey.json temp:/InfiniTDServer/data/
4. Cleanup the container: podman rm temp
5. Point master to an older commit: git update-ref refs/heads/master HEAD^
6. Push the latest commit to the server to trigger the post-recieve hook to build and start the container