process.env.NEXT_DIST_DIR = '.next-release';
process.argv = [process.execPath, require.resolve('next/dist/bin/next'), 'build'];
require('next/dist/bin/next');
