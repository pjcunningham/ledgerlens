import { Box, Typography } from '@mui/material';
import { Title, type RaRecord } from 'react-admin';
import { Column } from 'devextreme-react/data-grid';
import { DatagridDXRemote } from 'ra-devextreme-grid';

interface DemoCustomer extends RaRecord {
  id: number;
  account_ref: string;
  name: string;
  balance: number;
  active: boolean;
}

export function DemoCustomerList() {
  return (
    <Box sx={{ py: 3 }}>
      <Title title="LedgerLens · Demo customers" />
      <Typography variant="h4" component="h1" gutterBottom>
        Demo customers
      </Typography>
      <Typography sx={{ mb: 3 }}>
        Temporary foundation demo · 100 synthetic rows · No Sage data
      </Typography>
      <DatagridDXRemote<DemoCustomer>
        resource="demo-customers"
        paging={{ pageSize: 25 }}
        pager={{
          visible: true,
          allowedPageSizes: [10, 25, 50, 100],
          showPageSizeSelector: true,
          showInfo: true,
          showNavigationButtons: true,
        }}
        sorting={{ mode: 'multiple' }}
        filterRow={{ visible: false }}
        groupPanel={{ visible: false }}
        grouping={{ contextMenuEnabled: false }}
        allowColumnResizing
        allowColumnReordering
        columnChooser={{ enabled: true, mode: 'select' }}
        layoutPreferenceKey="ledgerlens.demo-customers.layout.v1"
        showBorders
        columnAutoWidth
      >
        <Column dataField="account_ref" caption="Account" dataType="string" />
        <Column dataField="name" caption="Customer Name" dataType="string" />
        <Column
          dataField="balance"
          caption="Balance"
          dataType="number"
          format={{ type: 'fixedPoint', precision: 2 }}
        />
        <Column dataField="active" caption="Active" dataType="boolean" />
      </DatagridDXRemote>
    </Box>
  );
}
