import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { newId } from './api';

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function sources(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}

describe('newId on a LAN trial over plain HTTP', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('uses crypto.randomUUID when the page is a secure context', () => {
    vi.stubGlobal('crypto', { randomUUID: () => '11111111-2222-4333-8444-555555555555', getRandomValues: () => { throw new Error('unused'); } });
    expect(newId()).toBe('11111111-2222-4333-8444-555555555555');
  });

  it('still returns distinct UUID v4 values when randomUUID is missing', () => {
    const real = globalThis.crypto;
    vi.stubGlobal('crypto', { getRandomValues: real.getRandomValues.bind(real) });
    const first = newId();
    const second = newId();
    expect(first).toMatch(UUID_V4);
    expect(second).toMatch(UUID_V4);
    expect(first).not.toBe(second);
  });

  it('keeps product code off the secure-context-only API', () => {
    const offenders = sources(join(__dirname))
      .filter((path) => !path.endsWith(join('src', 'api.ts')))
      .filter((path) => readFileSync(path, 'utf8').includes('crypto.randomUUID'));
    expect(offenders).toEqual([]);
  });
});
