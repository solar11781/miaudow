import { isRouteErrorResponse, useRouteError } from 'react-router-dom';
import { ButtonLink, Button } from '../design-system/Button';
import { useT } from './settings';

export function NotFound() {
  const t = useT();
  return (
    <main id="main" className="container band stack" style={{ ['--gap' as string]: '1.5rem', minHeight: '60vh' }}>
      <h1 className="h1">{t.errors.notFound}</h1>
      <ButtonLink to="/" icon="arrowRight">
        {t.errors.goHome}
      </ButtonLink>
    </main>
  );
}

export function RouteError() {
  const t = useT();
  const err = useRouteError();
  if (isRouteErrorResponse(err) && err.status === 404) return <NotFound />;
  return (
    <main id="main" className="container band stack" style={{ ['--gap' as string]: '1.5rem', minHeight: '60vh' }}>
      <h1 className="h2">{t.errors.crash}</h1>
      <div className="cluster">
        <Button onClick={() => window.location.reload()} icon="rotateR">
          {t.errors.reload}
        </Button>
        <ButtonLink to="/" variant="secondary">
          {t.errors.goHome}
        </ButtonLink>
      </div>
    </main>
  );
}
