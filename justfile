set dotenv-load

[doc('list recipes')]
[group('meta')]
[private]
@info:
    just --list

[arg('rpi', long, pattern='true|false', value='true', help='dry run')]
[doc('sync virtualenv')]
[group('build')]
@sync rpi='false':
    uv sync --compile-bytecode {{ if rpi == 'true' { '--extra rpi' } else { '' } }}
    uv run --no-sync prek install

[arg('host', long, help='remote host and target dir')]
[arg('commit', long, short='c', pattern='true|false', value='true', help='no dry run')]
[doc('upload tree to remote host')]
[group('build')]
rsync commit='false' host=env('RSYNC_HOST'):
    rsync --verbose --archive --delete \
        {{ if commit == 'true' { '' } else { '--dry-run' } }} \
        --exclude-from .gitignore \
        --exclude .pytest_cache \
        --exclude .ruff_cache \
        --exclude .git \
        . {{ host }}

[doc('run pre-commit')]
[group('dev')]
@prek:
    uv run --no-sync ruff format
    uv run --no-sync ruff check --fix
    uv run --no-sync ty check --fix

[doc('run all tests')]
[group('dev')]
@test *args='--quiet -n 4':
    COLUMNS=80 uv run --no-sync pytest {{ args }}
