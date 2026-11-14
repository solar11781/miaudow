import { Navigate, createHashRouter } from 'react-router-dom';
import { HomePage } from '../features/home/HomePage';
import { Layout } from './Layout';
import { NotFound, RouteError } from './RouteError';

// Hash routing: works from any static host or sub-folder without server rewrites. The home page ships in the main
// bundle (it is the usual landing page, one network round trip less); every other area loads on demand.
export const router = createHashRouter([
  {
    element: <Layout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: 'nong-dan',
        lazy: async () => ({ Component: (await import('../features/farmer/FarmerLayout')).FarmerLayout }),
        children: [
          { index: true, lazy: async () => ({ Component: (await import('../features/farmer/StartStep')).StartStep }) },
          { path: 'ruong', lazy: async () => ({ Component: (await import('../features/farmer/LandStep')).LandStep }) },
          { path: 'nam', lazy: async () => ({ Component: (await import('../features/farmer/YearsStep')).YearsStep }) },
          { path: 'uu-tien', lazy: async () => ({ Component: (await import('../features/farmer/PriorityStep')).PriorityStep }) },
          { path: 'phuong-an', lazy: async () => ({ Component: (await import('../features/farmer/PlansStep')).PlansStep }) },
        ],
      },
      { path: 'can-bo', lazy: async () => ({ Component: (await import('../features/officer/OfficerPage')).OfficerPage }) },
      { path: 'khoa-hoc', lazy: async () => ({ Component: (await import('../features/science/SciencePage')).SciencePage }) },
      { path: 'phuong-phap', lazy: async () => ({ Component: (await import('../features/method/MethodPage')).MethodPage }) },
      { path: 'dai-quan-sat', lazy: async () => ({ Component: (await import('../features/earth/EarthPage')).EarthPage }) },
      { path: 'bang-chung', lazy: async () => ({ Component: (await import('../features/evidence/EvidencePage')).EvidencePage }) },
      { path: 'tro-ly', lazy: async () => ({ Component: (await import('../features/ai/AssistantPage')).AssistantPage }) },
      { path: 'hoi', element: <Navigate to="/tro-ly" replace /> },
      { path: '*', element: <NotFound /> },
    ],
  },
]);
