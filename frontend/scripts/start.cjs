process.env.NEXT_DIST_DIR = '.next-release';
process.argv = [process.execPath, require.resolve('next/dist/bin/next'), 'start', '--hostname', '0.0.0.0', '--port', '3107'];
require('next/dist/bin/next');
