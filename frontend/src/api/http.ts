import { HttpError } from 'react-admin';

export async function requestJson(path: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new HttpError(`API request failed (HTTP ${response.status})`, response.status);
  }
  return response.json() as Promise<unknown>;
}
