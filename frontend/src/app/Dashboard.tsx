import { Button, Card, CardContent, Stack, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import { Title } from 'react-admin';
import { BackendReadiness } from '../components/BackendReadiness';

export function Dashboard() {
  return (
    <Card sx={{ mt: 3, maxWidth: 900 }}>
      <Title title="LedgerLens" />
      <CardContent>
        <Stack spacing={3} alignItems="flex-start">
          <Typography variant="overline">Phase 001 · Development foundation</Typography>
          <Typography variant="h3" component="h1">
            LedgerLens
          </Typography>
          <Typography>
            Read-only search, reporting, and analytics for Sage 50 Accounts. This early development
            build uses synthetic demo data. Sage synchronization is not implemented yet.
          </Typography>
          <BackendReadiness />
          <Button component={Link} to="/demo-customers" variant="contained">
            Open demo customers
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
