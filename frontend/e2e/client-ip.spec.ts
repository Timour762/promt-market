import { expect, test } from '@playwright/test';
import { trustedClientAddress } from '../src/lib/client-ip';

test('Render ignores spoofed first XFF address', () => {
  const headers = new Headers({
    'x-forwarded-for': '198.51.100.99, 203.0.113.7, 127.0.0.1',
    'cf-connecting-ip': '203.0.113.7',
  });
  expect(trustedClientAddress(headers, 'render')).toBe('203.0.113.7');
});

test('Render never falls back to XFF when its trusted header is missing', () => {
  expect(trustedClientAddress(new Headers({ 'x-forwarded-for': '198.51.100.99' }), 'render')).toBeNull();
});

test('Render accepts one valid IPv4 or IPv6 address', () => {
  for (const address of ['203.0.113.7', '2001:db8::1']) {
    expect(trustedClientAddress(new Headers({ 'cf-connecting-ip': address }), 'render')).toBe(address);
  }
});

test('Render rejects malformed addresses and lists', () => {
  for (const address of ['', 'invalid', '203.0.113.7, 198.51.100.99', '203.0.113.7:1234', '[2001:db8::1]']) {
    expect(trustedClientAddress(new Headers({
      'cf-connecting-ip': address,
      'x-forwarded-for': '198.51.100.99',
    }), 'render')).toBeNull();
  }
});

test('Caddy default preserves first forwarded address', () => {
  const headers = new Headers({ 'x-forwarded-for': '203.0.113.7, 127.0.0.1', 'cf-connecting-ip': '198.51.100.99' });
  expect(trustedClientAddress(headers)).toBe('203.0.113.7');
  expect(trustedClientAddress(headers, 'caddy')).toBe('203.0.113.7');
});

test('Unknown proxy source and missing Caddy address fail closed', () => {
  expect(trustedClientAddress(new Headers({ 'cf-connecting-ip': '203.0.113.7' }))).toBeNull();
  expect(trustedClientAddress(new Headers({ 'x-forwarded-for': '203.0.113.7' }), 'unknown')).toBeNull();
});
