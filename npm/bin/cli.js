#!/usr/bin/env node
/**
 * Bootstrap a fresh open-manim-slides project.
 *
 *   npx open-manim-slides@latest new my-deck
 *
 * Why an npm package for a Python framework: `npx <pkg>@latest` is the one
 * widely-available command that fetches the newest published version every
 * time it runs, with no global install to go stale. That is exactly what a
 * test run of the authoring workflow needs -- a project whose framework
 * code, skill files and artifact directories are all brand new, so what the
 * run measures is the skill's own guidance rather than whatever state a
 * long-lived development checkout has accumulated.
 *
 * This script installs nothing itself. It creates a project directory, puts
 * a Python virtualenv in it, installs the real `open-manim-slides`
 * distribution into that venv, and lets the distribution's own
 * `open-manim-slides init` lay down the skill files. Node is the delivery
 * mechanism, not a dependency of the framework.
 *
 * Deliberately zero npm dependencies: a bootstrapper that has to resolve a
 * dependency tree before it can start is a slower and more fragile thing
 * than the install it is bootstrapping.
 */

'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PKG = require('../package.json');
const REPO = 'https://github.com/lapotist/open-manim-slides';
const IS_WINDOWS = process.platform === 'win32';

function fail(message) {
  console.error(`\nerror: ${message}`);
  process.exit(1);
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: 'inherit', ...options });
  if (result.error) fail(`could not run ${command}: ${result.error.message}`);
  if (result.status !== 0) {
    fail(`${command} ${args.join(' ')} exited with status ${result.status}`);
  }
  return result;
}

function capture(command, args) {
  const result = spawnSync(command, args, { encoding: 'utf8' });
  if (result.error || result.status !== 0) return null;
  return (result.stdout || result.stderr || '').trim();
}

/** First python on PATH that is >= 3.10, or null. */
function findPython(explicit) {
  const candidates = explicit
    ? [explicit]
    : IS_WINDOWS
      ? ['py', 'python', 'python3']
      : ['python3', 'python'];
  for (const candidate of candidates) {
    const version = capture(candidate, [
      '-c',
      'import sys; print("%d.%d" % sys.version_info[:2])',
    ]);
    if (!version) continue;
    const [major, minor] = version.split('.').map(Number);
    if (major > 3 || (major === 3 && minor >= 10)) return { exe: candidate, version };
  }
  return null;
}

function venvBin(projectDir, name) {
  const dir = IS_WINDOWS ? 'Scripts' : 'bin';
  const exe = IS_WINDOWS ? `${name}.exe` : name;
  return path.join(projectDir, '.venv', dir, exe);
}

/**
 * Turn `--from` into a pip requirement.
 *
 * `pypi` pins the Python distribution to this npm package's own version, so
 * `npx open-manim-slides@1.2.3` and the framework it installs are the same
 * release rather than two things that drift apart. Anything unrecognised is
 * passed through untouched, which covers a local wheel or a checkout during
 * development.
 */
function requirementFor(from, ref) {
  if (from === 'pypi') return ref ? `open-manim-slides==${ref}` : `open-manim-slides==${PKG.version}`;
  if (from === 'git') return `git+${REPO}.git@${ref || 'main'}`;
  return from;
}

function parseArgs(argv) {
  const options = {
    command: null,
    directory: null,
    from: 'git',
    ref: null,
    python: null,
    force: false,
    install: true,
    extras: [],
  };
  const rest = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--from') options.from = argv[++i];
    else if (arg === '--ref') options.ref = argv[++i];
    else if (arg === '--python') options.python = argv[++i];
    else if (arg === '--force') options.force = true;
    else if (arg === '--no-install') options.install = false;
    else if (arg === '--web') options.extras.push('web');
    else if (arg === '--version' || arg === '-v') options.command = 'version';
    else if (arg === '--help' || arg === '-h') options.command = 'help';
    else if (arg.startsWith('-')) fail(`unknown option ${arg}`);
    else rest.push(arg);
  }
  if (!options.command) {
    options.command = rest.shift() || 'help';
    options.directory = rest.shift() || null;
  }
  return options;
}

const HELP = `
open-manim-slides ${PKG.version}

  npx open-manim-slides@latest new <directory>

Creates a deck project: a Python virtualenv with the framework installed,
the create-deck skill files, and an empty decks/ directory. Then open the
directory with your coding agent and ask it to build a deck.

Options
  --from <pypi|git|SPEC>  where to install the framework from
                          (default: git, i.e. the latest published source)
  --ref <ref>             git ref, or exact version when --from pypi
  --python <exe>          python interpreter to build the venv with
  --web                   also install the optional local web runner
  --force                 write into a non-empty directory
  --no-install            scaffold only; skip the venv and install

Requirements this cannot install for you: a C toolchain with cairo and
pango development headers (manim's manimpango builds against them), ffmpeg,
and a LaTeX distribution if your decks use MathTex/Tex. The generated
project can check them for you:

  .venv/bin/open-manim-slides doctor
`;

function main() {
  const options = parseArgs(process.argv.slice(2));

  if (options.command === 'version') {
    console.log(PKG.version);
    return;
  }
  if (options.command === 'help') {
    console.log(HELP.trim());
    return;
  }
  if (options.command !== 'new' && options.command !== 'init') {
    fail(`unknown command ${options.command}. Try: npx open-manim-slides new my-deck`);
  }
  if (!options.directory) {
    fail('a directory is required. Try: npx open-manim-slides new my-deck');
  }

  const projectDir = path.resolve(options.directory);
  if (fs.existsSync(projectDir)) {
    const entries = fs.readdirSync(projectDir).filter((name) => name !== '.git');
    if (entries.length > 0 && !options.force) {
      fail(`${projectDir} is not empty. Re-run with --force to write into it anyway.`);
    }
  }
  fs.mkdirSync(projectDir, { recursive: true });

  if (!options.install) {
    console.log(`Created ${projectDir} (--no-install: no venv, no skill files).`);
    return;
  }

  const python = findPython(options.python);
  if (!python) {
    fail(
      'no Python >= 3.10 found on PATH. Install one, or pass --python <exe>.'
    );
  }
  console.log(`\nPython ${python.version} (${python.exe})`);

  console.log('\nCreating .venv ...');
  run(python.exe, ['-m', 'venv', path.join(projectDir, '.venv')]);

  const requirement = requirementFor(options.from, options.ref);
  const spec = options.extras.length
    ? // pip needs the extras attached to the requirement, and a URL
      // requirement takes them in brackets before the @ -- simplest correct
      // form for both cases is the PEP 508 `pkg[extra] @ url` spelling.
      requirement.includes('://')
      ? `open-manim-slides[${options.extras.join(',')}] @ ${requirement.replace(/^git\+/, 'git+')}`
      : requirement.replace('open-manim-slides', `open-manim-slides[${options.extras.join(',')}]`)
    : requirement;

  console.log(`\nInstalling ${spec}`);
  console.log('(manim is a large dependency; the first run takes a few minutes)\n');
  run(venvBin(projectDir, 'python'), ['-m', 'pip', 'install', '--disable-pip-version-check', spec]);

  console.log('\nWriting the project scaffold ...');
  run(venvBin(projectDir, 'open-manim-slides'), ['init', projectDir]);

  console.log('\nChecking the environment ...');
  spawnSync(venvBin(projectDir, 'open-manim-slides'), ['doctor'], { stdio: 'inherit' });

  const activate = IS_WINDOWS ? '.venv\\Scripts\\activate' : 'source .venv/bin/activate';
  // A relative path that climbs out of the cwd is longer and harder to read
  // than the absolute one it is derived from.
  const relative = path.relative(process.cwd(), projectDir);
  const shown = !relative || relative.startsWith('..') ? projectDir : relative;
  console.log(`
Done. Next:

  cd ${shown}
  ${activate}

Then open this directory with your coding agent and ask it to build a deck,
e.g. "create a deck introducing the Pythagorean theorem for high school".
`);
}

main();
