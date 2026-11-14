import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import './styles/global.css';
import { router } from './app/router';
import { SettingsProvider } from './app/settings';
import { ProvenanceProvider } from './features/provenance/ProvenanceProvider';

const root = document.getElementById('root');
if (!root) throw new Error('missing #root');

createRoot(root).render(
  <StrictMode>
    <SettingsProvider>
      <ProvenanceProvider>
        <RouterProvider router={router} />
      </ProvenanceProvider>
    </SettingsProvider>
  </StrictMode>,
);
