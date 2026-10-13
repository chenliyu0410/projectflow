import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';
import useScrollActivity from './useScrollActivity';

function Root() {
  useScrollActivity();
  return <App />;
}

createRoot(document.getElementById('root')!).render(<StrictMode><Root /></StrictMode>);
