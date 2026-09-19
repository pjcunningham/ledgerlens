import { Admin, Resource, defaultLightTheme } from 'react-admin';
import { dataProvider } from './api/dataProvider';
import { Dashboard } from './app/Dashboard';
import { DemoCustomerList } from './resources/demo-customers/DemoCustomerList';

export function App() {
  return (
    // Keep the application theme aligned with the fixed DevExtreme dx.light.css theme.
    <Admin
      title="LedgerLens"
      dataProvider={dataProvider}
      dashboard={Dashboard}
      theme={defaultLightTheme}
    >
      <Resource
        name="demo-customers"
        options={{ label: 'Demo customers' }}
        list={DemoCustomerList}
      />
    </Admin>
  );
}
