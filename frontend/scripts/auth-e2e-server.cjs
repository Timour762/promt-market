// Dedicated loopback test server with a graceful stop on Windows and Unix.
// Test routes are defined by this launcher and never added to the application.
const http = require('node:http');
const next = require('next');
const app = next({ dev: true, hostname: '127.0.0.1', port: 3137 });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const server = http.createServer((request, response) => {
    if (request.method === 'POST' && request.url === '/__auth_test_shutdown') {
      response.writeHead(200, { 'Content-Type': 'application/json' });
      response.end('{"status":"stopping"}');
      setTimeout(async () => {
        server.close();
        await app.close();
        process.exit(0);
      }, 100);
      return;
    }
    return handle(request, response);
  });
  server.listen(3137, '127.0.0.1');
}).catch(() => {
  console.error('Unable to start auth browser test web server');
  process.exit(1);
});
