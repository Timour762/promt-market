export default async function teardown() {
  try { await fetch('http://127.0.0.1:8117/__test_shutdown', { method: 'POST', signal: AbortSignal.timeout(3000) }); }
  catch { /* Playwright also terminates the owned test server. */ }
}
