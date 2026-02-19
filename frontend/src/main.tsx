import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import App from './App';
import { TabletApp } from './TabletApp';
import { TransferPage } from './pages/TransferPage';
import { useIsTablet } from './hooks/useIsTablet';

function Root() {
  const isTablet = useIsTablet();

  return (
    <Routes>
      <Route path="/" element={isTablet ? <TabletApp /> : <App />} />
      <Route path="/transfer" element={<TransferPage />} />
      <Route path="/transfer/:sessionId" element={<TransferPage />} />
    </Routes>
  );
}

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <Root />
    </BrowserRouter>
  </React.StrictMode>
);
