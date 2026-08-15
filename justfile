set dotenv-load

[doc('list recipes')]
[group('meta')]
[private]
@info:
    just --list

[doc('create or sync virtualenv')]
[group('build')]
sync:
    uv sync --compile-bytecode

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
        --exclude .git \
        . {{ host }}

[arg('dry', long, short, pattern='true|false', value='true', help='dry run')]
[doc('run pre-commit checks')]
[group('lint')]
@check dry='false':
    uv run --no-sync ruff format {{ if dry == 'true' { '--check' } else { '' } }}
    uv run --no-sync ruff check {{ if dry == 'true' { '' } else { '--fix' } }}
    uv run --no-sync ty check {{ if dry == 'true' { '' } else { '--fix' } }}

[arg('renew', long, short, pattern='true|false', value='true', help='re-record HTTP cassettes against the live API')]
[doc('run test suite')]
[group('lint')]
@test renew='false':
    uv run --no-sync pytest \
        {{ if renew == 'true' { '--record-mode rewrite' } else { '' } }} \
        --quiet
