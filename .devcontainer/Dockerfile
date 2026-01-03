FROM ubuntu:latest

ARG USER=developer
ARG DEBIAN_FRONTEND=noninteractive
RUN apt update \
    && apt install -y --no-install-recommends sudo git zsh curl wget ca-certificates \
    && apt clean \
    && apt autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /usr/bin/zsh ${USER} \
    && echo "${USER} ALL=(ALL) NOPASSWD: ALL" >/etc/sudoers.d/${USER} \
    && chmod 0440 /etc/sudoers.d/${USER}


USER ${USER}
ARG HOME=/home/${USER}
ARG ZSH=${HOME}/.oh-my-zsh
ARG ZSH_CUSTOM=${ZSH}/custom
WORKDIR ${HOME}


RUN <<EOT
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
    mkdir -p ${ZSH_CUSTOM}
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM}/plugins/zsh-autosuggestions
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM}/plugins/zsh-syntax-highlighting
    sed -i.bak 's/plugins=(\(.*\))/plugins=(\1 zsh-autosuggestions zsh-syntax-highlighting)/' ~/.zshrc
EOT


ARG SPACESHIP_REMOTE=https://github.com/spaceship-prompt/spaceship-prompt.git
RUN <<EOT
    git clone ${SPACESHIP_REMOTE} ${ZSH_CUSTOM}/themes/spaceship-prompt --depth=1
    ln -s ${ZSH_CUSTOM}/themes/spaceship-prompt/spaceship.zsh-theme ${ZSH_CUSTOM}/themes/spaceship.zsh-theme
    sed -i 's|ZSH_THEME="robbyrussell"|ZSH_THEME="spaceship"|g' .zshrc
EOT


RUN <<EOT
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo 'eval "$(uv generate-shell-completion zsh)"' >> ~/.zshrc
    echo 'eval "$(uvx --generate-shell-completion zsh)"' >> ~/.zshrc
EOT

RUN <<EOT
    sudo apt-get update && sudo apt-get install -y \
    portaudio19-dev libportaudio2 libportaudiocpp0 \
    alsa-utils pulseaudio \
    && sudo rm -rf /var/lib/apt/lists/*
EOT

# add git shortcut aliases for convenience
RUN <<EOT
    echo '\n# Git power shortcuts' >> ~/.zshrc
    # Pretty helpers
    echo 'alias gs="git status -sb"' >> ~/.zshrc
    echo 'alias gl="git log --oneline --decorate --graph -15"' >> ~/.zshrc
    echo 'alias gco="git checkout"' >> ~/.zshrc
    echo 'alias gcm="git commit -m"' >> ~/.zshrc
    echo 'alias gcan="git commit --amend --no-edit"' >> ~/.zshrc
    # Confirm helper
    echo '_git_confirm() {' >> ~/.zshrc
    echo '  printf "Continue? [y/N]: "' >> ~/.zshrc
    echo '  read -r reply' >> ~/.zshrc
    echo '  [ "$reply" = "y" ] || [ "$reply" = "Y" ]' >> ~/.zshrc
    echo '}' >> ~/.zshrc
    # Undo last commit locally + remotely
    echo 'gundo() {' >> ~/.zshrc
    echo '  branch=$(git symbolic-ref --short HEAD 2>/dev/null) || return' >> ~/.zshrc
    echo '  git log -1 --oneline' >> ~/.zshrc
    echo '  _git_confirm || return' >> ~/.zshrc
    echo '  git reset --soft HEAD~1 || return' >> ~/.zshrc
    echo '  git push --force-with-lease origin "$branch"' >> ~/.zshrc
    echo '}' >> ~/.zshrc
    # Squash branch commits into one
    echo 'gsquash() {' >> ~/.zshrc
    echo '  base=${1:-main}' >> ~/.zshrc
    echo '  git fetch origin "$base" || return' >> ~/.zshrc
    echo '  _git_confirm || return' >> ~/.zshrc
    echo '  git reset --soft "$(git merge-base HEAD origin/$base)" || return' >> ~/.zshrc
    echo '  git commit' >> ~/.zshrc
    echo '}' >> ~/.zshrc
    # Rebase onto a remote branch
    echo 'grebase() {' >> ~/.zshrc
    echo '  target=$1' >> ~/.zshrc
    echo '  [ -z "$target" ] && echo "Usage: grebase origin/main" && return 1' >> ~/.zshrc
    echo '  _git_confirm || return' >> ~/.zshrc
    echo '  git fetch "${target%%/*}" || return' >> ~/.zshrc
    echo '  git rebase "$target"' >> ~/.zshrc
    echo '}' >> ~/.zshrc
    # Fetch remote branch and rebase current branch onto it
    echo 'graft() {' >> ~/.zshrc
    echo '  branch=$1' >> ~/.zshrc
    echo '  [ -z "$branch" ] && echo "Usage: graft branch-name" && return 1' >> ~/.zshrc
    echo '  _git_confirm || return' >> ~/.zshrc
    echo '  git fetch origin "$branch" || return' >> ~/.zshrc
    echo '  git rebase "origin/$branch"' >> ~/.zshrc
    echo '}' >> ~/.zshrc
EOT
