export default async function teardown() {
  for (const port of [8137, 3137]) {
    try {
      await fetch(`http://127.0.0.1:${port}/__auth_test_shutdown`, { method: 'POST', signal: AbortSignal.timeout(3000) });
    } catch { /* Playwright also terminates the owned test servers. */ }
  }
}
