set dotenv-load

[doc('list recipes')]
[group('meta')]
[private]
@info:
    just --list

[doc('sync virtualenv')]
[arg('rpi', long, short, pattern='true|false', value='true', help='dry run')]
[group('build')]
@sync rpi='false':
    uv sync --compile-bytecode {{ if rpi == 'true' { '--extra rpi' } else { '' } }}
    uv run --no-sync prek install

[arg('host', long, short, help='remote host and target dir')]
[arg('commit', long, short, pattern='true|false', value='true', help='no dry run')]
[doc('upload working tree to remote host')]
[group('build')]
rsync commit='false' host=env('REMOTE'):
    rsync --verbose --archive --delete \
        {{ if commit == 'true' { '' } else { '--dry-run' } }} \
        --exclude-from .gitignore \
        --exclude .pytest_cache \
        --exclude .ruff_cache \
        . {{ host }}

[doc('build wheel')]
[group('build')]
@wheel:
    uv build --wheel

[doc('run pre-commit checks')]
[arg('staged', long, short, pattern='true|false', value='true', help='only check staged files')]
[group('test')]
@check staged='false':
    prek run {{ if staged == 'true' { '' } else { '--all-files' } }} 

[arg('renew', long, short, pattern='true|false', value='true', help='re-record HTTP cassettes against the live API')]
[doc('run test suite')]
[group('test')]
@test renew='false' *flags='--quiet':
    uv run --no-sync pytest \
        {{ if renew == 'true' { '--record-mode rewrite' } else { '' } }} \
        {{ flags }}
