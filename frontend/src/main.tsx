import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import './styles/global.css';
import { router } from './app/router';
import { SettingsProvider } from './app/settings';
import { ProvenanceProvider } from './features/provenance/ProvenanceProvider';
import { AccountProvider } from './features/account/AccountProvider';

const root = document.getElementById('root');
if (!root) throw new Error('missing #root');

createRoot(root).render(
  <StrictMode>
    <SettingsProvider>
      <ProvenanceProvider>
        <AccountProvider>
          <RouterProvider router={router} />
        </AccountProvider>
      </ProvenanceProvider>
    </SettingsProvider>
  </StrictMode>,
);
