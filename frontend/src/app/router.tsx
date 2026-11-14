import { useLayoutEffect } from 'react';
import { Navigate, Outlet, createHashRouter, type RouteObject } from 'react-router-dom';
import { HomePage } from '../features/home/HomePage';
import { Layout } from './Layout';
import { EN_HOME, EN_SEGMENT } from './paths';
import { NotFound, RouteError } from './RouteError';
import { useSettings, type Lang } from './settings';

/** Every page under its Vietnamese path, or its English one (D-174); the same components either way. */
function pages(lang: Lang): RouteObject[] {
  const p = (vi: string) => (lang === 'en' ? (EN_SEGMENT[vi] ?? vi) : vi);
  return [
    {
      path: p('nong-dan'),
      lazy: async () => ({ Component: (await import('../features/farmer/FarmerLayout')).FarmerLayout }),
      children: [
        { index: true, lazy: async () => ({ Component: (await import('../features/farmer/StartStep')).StartStep }) },
        { path: p('ruong'), lazy: async () => ({ Component: (await import('../features/farmer/LandStep')).LandStep }) },
        { path: p('nam'), lazy: async () => ({ Component: (await import('../features/farmer/YearsStep')).YearsStep }) },
        {
          path: p('uu-tien'),
          lazy: async () => ({ Component: (await import('../features/farmer/PriorityStep')).PriorityStep }),
        },
        {
          path: p('phuong-an'),
          lazy: async () => ({ Component: (await import('../features/farmer/PlansStep')).PlansStep }),
        },
      ],
    },
    {
      path: p('can-bo'),
      lazy: async () => ({ Component: (await import('../features/officer/OfficerPage')).OfficerPage }),
    },
    {
      path: p('khoa-hoc'),
      lazy: async () => ({ Component: (await import('../features/science/SciencePage')).SciencePage }),
    },
    {
      path: p('phuong-phap'),
      lazy: async () => ({ Component: (await import('../features/method/MethodPage')).MethodPage }),
    },
    {
      path: p('dai-quan-sat'),
      lazy: async () => ({ Component: (await import('../features/earth/EarthPage')).EarthPage }),
    },
    {
      path: p('bang-chung'),
      lazy: async () => ({ Component: (await import('../features/evidence/EvidencePage')).EvidencePage }),
    },
    {
      path: p('tro-ly'),
      lazy: async () => ({ Component: (await import('../features/ai/AssistantPage')).AssistantPage }),
    },
    {
      path: p('dang-nhap'),
      lazy: async () => ({ Component: (await import('../features/account/SignInPage')).SignInPage }),
    },
    {
      path: p('da-luu'),
      lazy: async () => ({ Component: (await import('../features/account/SavedPage')).SavedPage }),
    },
  ];
}

/** An English path opens its page in English: the language is set before the page paints, and nothing is stored. */
function InEnglish() {
  const { setLang } = useSettings();
  useLayoutEffect(() => setLang('en'), [setLang]);
  return <Outlet />;
}

// Hash routing: works from any static host or sub-folder without server rewrites. The home page ships in the main
// bundle (it is the usual landing page, one network round trip less); every other area loads on demand. The English
// paths render the same components rather than redirecting, so the address the farmer shares stays in English.
export const router = createHashRouter([
  {
    element: <Layout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <HomePage /> },
      ...pages('vi'),
      { element: <InEnglish />, children: [{ path: EN_HOME.slice(1), element: <HomePage /> }, ...pages('en')] },
      { path: 'hoi', element: <Navigate to="/tro-ly" replace /> },
      { path: '*', element: <NotFound /> },
    ],
  },
]);
