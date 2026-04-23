# Git hooks 

post-commit: Warn after commit if requirements.txt or dev-requirements.txt is out of sync

## Installation

Copy or link the files to .git/hooks.

Copying:

cp hooks/post-commit .git/hooks/post-commit

Linking (hook will be updated automatically if it changes in the repo):

ln -rs hooks/post-commit .git/hooks/post-commit
