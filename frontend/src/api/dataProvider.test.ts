import { afterEach, describe, expect, it, vi } from 'vitest';
import { dataProvider } from './dataProvider';

afterEach(() => vi.unstubAllGlobals());

describe('getGrid transport', () => {
  it('posts the load options to the explicit endpoint and returns the remote result', async () => {
    const result = { data: [{ id: 26, name: 'Demo Customer 026' }], totalCount: 100 };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(result)));
    vi.stubGlobal('fetch', fetchMock);
    const loadOptions = {
      skip: 25,
      take: 25,
      requireTotalCount: true,
      sort: [{ selector: 'name', desc: true }],
    };
    await expect(dataProvider.getGrid('demo-customers', { loadOptions })).resolves.toEqual(result);
    expect(fetchMock).toHaveBeenCalledWith('/api/demo/customers/grid', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ loadOptions }),
    });
  });

  it.each(['customers', '../health/ready', 'toString', '__proto__'])(
    'rejects unknown resource %s before making a request',
    async (resource) => {
      const fetchMock = vi.fn();
      vi.stubGlobal('fetch', fetchMock);
      await expect(dataProvider.getGrid(resource, { loadOptions: {} })).rejects.toThrow(
        'Unsupported grid resource',
      );
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it.each([422, 500, 503])('rejects HTTP %s', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('failure', { status })));
    await expect(dataProvider.getGrid('demo-customers', { loadOptions: {} })).rejects.toThrow(
      `HTTP ${status}`,
    );
  });

  it('rejects a network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network unavailable')));
    await expect(dataProvider.getGrid('demo-customers', { loadOptions: {} })).rejects.toThrow(
      'Network unavailable',
    );
  });

  it('rejects an invalid response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"rows":[]}')));
    await expect(dataProvider.getGrid('demo-customers', { loadOptions: {} })).rejects.toThrow(
      'Invalid grid response',
    );
  });

  it('rejects unsupported CRUD operations explicitly', async () => {
    await expect(dataProvider.getOne('demo-customers', { id: 1 })).rejects.toThrow('not supported');
    await expect(dataProvider.create('demo-customers', { data: { name: 'New' } })).rejects.toThrow(
      'not supported',
    );
  });
});
