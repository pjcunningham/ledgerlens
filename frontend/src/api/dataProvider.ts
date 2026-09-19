import type { RaRecord } from 'react-admin';
import type { DatagridDXDataProvider, GetGridParams, GetGridResult } from 'ra-devextreme-grid';
import { requestJson } from './http';

const endpoints = new Map([['demo-customers', '/api/demo/customers/grid']]);

async function unsupported(): Promise<never> {
  throw new Error('This operation is not supported by the Phase 001 read-only demo.');
}

export const dataProvider: DatagridDXDataProvider = {
  getList: unsupported,
  getOne: unsupported,
  getMany: unsupported,
  getManyReference: unsupported,
  create: unsupported,
  update: unsupported,
  updateMany: unsupported,
  delete: unsupported,
  deleteMany: unsupported,
  async getGrid<RecordType extends RaRecord = RaRecord>(
    resource: string,
    params: GetGridParams,
  ): Promise<GetGridResult<RecordType>> {
    const endpoint = endpoints.get(resource);
    if (!endpoint) throw new Error(`Unsupported grid resource: ${resource}`);
    const result = await requestJson(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ loadOptions: params.loadOptions }),
    });
    if (
      typeof result !== 'object' ||
      result === null ||
      !('data' in result) ||
      !Array.isArray(result.data)
    ) {
      throw new Error('Invalid grid response: expected a data array.');
    }
    // The remote grid validates counts and row identifiers. RecordType is the
    // resource's compile-time contract; JSON cannot establish a generic TS type.
    return result as GetGridResult<RecordType>;
  },
};
