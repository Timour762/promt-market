const fs = require('node:fs');
const path = require('node:path');
const root = fs.realpathSync.native(path.resolve(__dirname, '..'));
process.chdir(root);
process.argv = [process.execPath, require.resolve('next/dist/bin/next'), 'dev', root, '--hostname', '127.0.0.1', '--port', '3107'];
require('next/dist/bin/next');
