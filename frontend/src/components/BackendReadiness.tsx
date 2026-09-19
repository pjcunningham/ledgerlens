import { useEffect, useState } from 'react';
import { Alert } from '@mui/material';
import { requestJson } from '../api/http';

export function BackendReadiness() {
  const [state, setState] = useState<'checking' | 'ready' | 'unavailable'>('checking');
  useEffect(() => {
    const controller = new AbortController();
    void requestJson('/api/health/ready', { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) {
          setState(
            typeof result === 'object' &&
              result !== null &&
              'status' in result &&
              result.status === 'ready'
              ? 'ready'
              : 'unavailable',
          );
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setState('unavailable');
      });
    return () => controller.abort();
  }, []);
  return (
    <Alert severity={state === 'ready' ? 'success' : state === 'checking' ? 'info' : 'warning'}>
      {state === 'checking'
        ? 'Checking backend readiness…'
        : state === 'ready'
          ? 'Backend ready · PostgreSQL and Typesense connected'
          : 'Backend not ready · Check the API, PostgreSQL, and Typesense services'}
    </Alert>
  );
}
