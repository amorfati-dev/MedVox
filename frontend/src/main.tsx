import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import App from './App';
import { TransferPage } from './pages/TransferPage';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/transfer" element={<TransferPage />} />
        <Route path="/transfer/:sessionId" element={<TransferPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
